import asyncio
import csv
import json

import pytest

import Engagement_Manager as em
from Engagement_Manager import EngagementManager


@pytest.fixture
def manager(tmp_path):
    return EngagementManager(record_dir=tmp_path)


@pytest.fixture
def populated(manager):
    manager.process_track_batch(EngagementManager.generate_fake_tracks())
    return manager


# ── receive loop ─────────────────────────────────────────────────────────────
def test_process_track_batch_updates_tracks(populated):
    assert set(populated.active_tracks) == {"TRK-101", "TRK-102"}
    assert populated.active_tracks["TRK-101"]["position"] == (34.05, -118.24)


def test_later_update_overwrites_track(populated):
    row = EngagementManager.generate_fake_tracks()[0] | {"classification": "Unknown"}
    populated.process_track_batch([row])
    assert populated.active_tracks["TRK-101"]["classification"] == "Unknown"
    assert len(populated.active_tracks) == 2


# ── operator loop ────────────────────────────────────────────────────────────
def test_engage_success_consumes_resource(populated):
    eng_id = populated.engage("TRK-101", "interceptors")
    assert eng_id == "ENG-1"
    assert populated.resources["interceptors"] == 9
    assert populated.engagements["ENG-1"]["status"] == "Initiated"


def test_engage_refused_for_unknown_track(populated):
    assert populated.engage("TRK-999", "interceptors") is None
    assert populated.resources["interceptors"] == 10
    assert populated.engagements == {}


def test_engage_refused_when_resources_depleted(tmp_path):
    m = EngagementManager(record_dir=tmp_path, resources={"interceptors": 1})
    m.process_track_batch(EngagementManager.generate_fake_tracks())
    assert m.engage("TRK-101", "interceptors") == "ENG-1"
    assert m.engage("TRK-102", "interceptors") is None
    assert m.resources["interceptors"] == 0


def test_engagement_ids_increment(populated):
    assert [populated.engage("TRK-101", "interceptors") for _ in range(3)] == ["ENG-1", "ENG-2", "ENG-3"]


def test_operator_action_runs_after_delay(populated, monkeypatch):
    async def no_wait(_):
        return None
    monkeypatch.setattr(em.asyncio, "sleep", no_wait)
    asyncio.run(populated._simulate_operator_action())
    assert "ENG-1" in populated.engagements


# ── recording ────────────────────────────────────────────────────────────────
def test_csv_round_trip(manager):
    rows = EngagementManager.generate_fake_tracks()
    path = manager.write_records(rows)
    assert path.suffix == ".csv"
    with open(path, newline="") as f:
        back = list(csv.DictReader(f))
    assert [r["track_id"] for r in back] == ["TRK-101", "TRK-102"]
    assert list(back[0]) == em.FIELDNAMES


def test_two_writes_never_collide(manager):
    rows = EngagementManager.generate_fake_tracks()
    assert manager.write_records(rows) != manager.write_records(rows)
    assert len(list(manager.record_dir.glob("*.csv"))) == 2


def test_invalid_format_rejected(tmp_path):
    with pytest.raises(ValueError):
        EngagementManager(record_dir=tmp_path, record_format="xlsx")


def test_parquet_falls_back_to_csv_without_pyarrow(tmp_path, monkeypatch):
    monkeypatch.setattr(em, "HAVE_PYARROW", False)
    m = EngagementManager(record_dir=tmp_path, record_format="parquet")
    assert m.record_format == "csv"


def test_parquet_round_trip_keeps_types(tmp_path):
    pa = pytest.importorskip("pyarrow")
    m = EngagementManager(record_dir=tmp_path, record_format="parquet")
    m.write_records(EngagementManager.generate_fake_tracks())
    m.write_records(EngagementManager.generate_fake_tracks())
    table = m.load_parquet_records()
    assert table.num_rows == 4
    assert table.schema.field("timestamp").type == pa.timestamp("us", tz="UTC")
    assert table.schema.field("validity").type == pa.float64()
    assert sorted(set(table.column("track_id").to_pylist())) == ["TRK-101", "TRK-102"]


# ── broadcast loop ───────────────────────────────────────────────────────────
def test_state_payload_is_json_serializable(populated):
    populated.engage("TRK-101", "interceptors")
    payload = json.loads(json.dumps(populated.build_state_payload()))
    assert payload["tracked_objects_count"] == 2
    assert payload["remaining_resources"]["interceptors"] == 9
    assert payload["active_engagements"]["ENG-1"]["track_id"] == "TRK-101"
