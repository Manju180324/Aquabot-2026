from __future__ import annotations

from typing import Any


def pipeline_stages(telemetry: dict[str, Any], detection_count: int = 0) -> list[dict[str, Any]]:
    """Describe stages using only counts present in this run and source dataframe."""
    received = int(telemetry.get("received", 0))
    processed = int(telemetry.get("processed", 0))
    rejected = int(telemetry.get("rejected", 0))
    loaded = received > 0
    valid_schema = bool(telemetry.get("required_present", False))
    cleaned_status = "complete" if valid_schema and loaded else ("warning" if loaded else "pending")
    return [
        {"stage": "Data collection", "state": "complete" if loaded else "pending", "received": received, "processed": received, "rejected": 0, "evidence": "Recorded CSV rows; no live sensor connection is configured."},
        {"stage": "Data ingestion", "state": "complete" if loaded else "pending", "received": received, "processed": received, "rejected": 0, "evidence": "Rows read from the selected CSV source."},
        {"stage": "Data cleaning", "state": cleaned_status, "received": received, "processed": processed, "rejected": rejected, "evidence": "Retains rows with parseable timestamp and GPS coordinates; rejected count is measured."},
        {"stage": "Preprocessing", "state": "complete" if valid_schema and loaded else "pending", "received": processed, "processed": processed, "rejected": 0, "evidence": "Timestamp and GPS fields parsed; available numeric fields converted where possible."},
        {"stage": "Feature extraction", "state": "complete" if valid_schema and loaded else "pending", "received": processed, "processed": processed, "rejected": 0, "evidence": "Existing CSV fields are exposed for charts and route visualization; no additional features are synthesized."},
        {"stage": "Analysis / anomaly detection", "state": "not configured", "received": processed, "processed": 0, "rejected": 0, "evidence": "No anomaly detector is implemented for the recorded telemetry fields. Water-quality simulation has its separate existing composite score."},
        {"stage": "Storage", "state": "complete" if loaded else "pending", "received": received, "processed": received, "rejected": 0, "evidence": "Source remains the selected CSV; no telemetry database write is performed."},
        {"stage": "Dashboard visualization", "state": "complete" if loaded else "pending", "received": processed, "processed": processed, "rejected": 0, "evidence": f"Camera detections recorded in this Streamlit session: {detection_count}."},
    ]
