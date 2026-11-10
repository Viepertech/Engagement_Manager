import asyncio
import json
import logging
import csv
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# CONFIGURABLE DIRECTORY LOCATION ON UBUNTU
ENGAGEMENT_RECORD_DIR = Path("/home/vipertech/Python_Box/engagement_record")

class EngagementManager:
    def __init__(self, host="127.0.0.1", rx_port=5555, tx_port=5556):
        self.host = host
        self.rx_port = rx_port
        self.tx_port = tx_port
        
        # Ensure the output directory exists on startup
        ENGAGEMENT_RECORD_DIR.mkdir(parents=True, exist_ok=True)
        
        # State management
        self.active_tracks = {}
        self.resources = {"interceptors": 10, "support_units": 5}
        self.engagements = {}

    async def start(self):
        """Starts the concurrent receive loop, operator simulation, and state machine."""
        logging.info("Engagement Manager screen initializing...")
        await asyncio.gather(
            self._simulate_receive_stream(),
            self._simulate_operator_action(), # <--- Added operator workflow
            self._state_broadcast_loop()
        )

    async def _simulate_receive_stream(self):
        """Simulates receiving data streams and writing them via built-in CSV."""
        while True:
            await asyncio.sleep(3)
            
            # UTC timestamp for the batch data records
            current_time = datetime.now(timezone.utc).isoformat()
            
            incoming_rows = [
                {
                    'timestamp': current_time,
                    'track_id': 'TRK-101',
                    'classification': 'Hostile',
                    'validity': 0.95,
                    'position_x': 34.05,
                    'position_y': -118.24
                },
                {
                    'timestamp': current_time,
                    'track_id': 'TRK-102',
                    'classification': 'Neutral',
                    'validity': 0.88,
                    'position_x': 35.12,
                    'position_y': -118.40
                }
            ]
            
            self._process_track_batch(incoming_rows)
            self._write_to_csv(incoming_rows)

    def _process_track_batch(self, rows):
        """Updates internal track states using incoming row dictionaries."""
        for row in rows:
            t_id = row['track_id']
            self.active_tracks[t_id] = {
                "classification": row['classification'],
                "validity": row['validity'],
                "position": (row['position_x'], row['position_y'])
            }
        logging.info(f"Updated state with {len(rows)} tracks.")

    async def _simulate_operator_action(self):
        """Simulates an operator analyzing the screen and deciding to engage a track."""
        await asyncio.sleep(6) # Wait 6 seconds for tracks to populate
        
        # Simulate operator decision: engage TRK-101 using an interceptor resource
        target_track = "TRK-101"
        resource_needed = "interceptors"
        
        if target_track in self.active_tracks and self.resources.get(resource_needed, 0) > 0:
            self.resources[resource_needed] -= 1
            engagement_id = f"ENG-{len(self.engagements) + 1}"
            
            self.engagements[engagement_id] = {
                "track_id": target_track,
                "resource_type": resource_needed,
                "status": "Initiated",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            logging.info(f"--- OPERATOR ACTION --- Initiated {engagement_id} on {target_track} using {resource_needed}!")
        else:
            logging.warning("Operator action failed: Track missing or resources depleted.")

    def _write_to_csv(self, rows):
        """Writes incoming rows to a unique UTC timestamped CSV file."""
        try:
            utc_now = datetime.now(timezone.utc)
            timestamp_str = utc_now.strftime("%Y%m%d_%H%M%S")
            file_path = ENGAGEMENT_RECORD_DIR / f"engagement_{timestamp_str}.csv"
            
            fieldnames = ['timestamp', 'track_id', 'classification', 'validity', 'position_x', 'position_y']
            with open(file_path, mode='w', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
                writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            
            logging.info(f"Successfully wrote CSV file: {file_path}")
        except Exception as e:
            logging.error(f"Failed to write CSV file to disk: {e}")

    async def _state_broadcast_loop(self):
        """Broadcasts active engagement and system state."""
        while True:
            await asyncio.sleep(5)
            payload = {
                "active_engagements": self.engagements,
                "remaining_resources": self.resources,
                "tracked_objects_count": len(self.active_tracks)
            }
            logging.info(f"[BROADCAST] State published -> {json.dumps(payload)}")

if __name__ == "__main__":
    manager = EngagementManager()
    try:
        asyncio.run(manager.start())
    except KeyboardInterrupt:
        logging.info("Engagement Manager shut down by operator.")