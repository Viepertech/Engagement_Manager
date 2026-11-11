FROM python:3.12-slim

WORKDIR /app
COPY requirements-optional.txt .
RUN pip install --no-cache-dir -r requirements-optional.txt

COPY Engagement_Manager.py .

# Run as a non-root user; records go to a volume-friendly directory
RUN useradd --create-home appuser && mkdir -p /app/engagement_record && chown appuser /app/engagement_record
USER appuser

ENV PYTHONUNBUFFERED=1 \
    ENGAGEMENT_RECORD_DIR=/app/engagement_record \
    RECORD_FORMAT=parquet

CMD ["python", "Engagement_Manager.py"]
