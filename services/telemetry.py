from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

from config.settings import DEFAULT_TELEMETRY_PATH


REQUIRED_TELEMETRY_FIELDS = ("timestamp", "gps_lat", "gps_lon")
KNOWN_SENSOR_FIELDS = ("speed", "ultrasonic", "lora_rssi", "lora_snr")
FIELD_LABELS = {
    "speed": ("Speed", "CSV units not specified"),
    "ultrasonic": ("Ultrasonic", "CSV units not specified"),
    "lora_rssi": ("LoRa RSSI", "CSV units not specified"),
    "lora_snr": ("LoRa SNR", "CSV units not specified"),
    "x": ("Local X", "CSV units not specified"),
    "y": ("Local Y", "CSV units not specified"),
    "gps_lat": ("Latitude", "degrees"),
    "gps_lon": ("Longitude", "degrees"),
}


def load_telemetry(upload: Any = None, path: Path = DEFAULT_TELEMETRY_PATH) -> tuple[pd.DataFrame, str]:
    """Load the supplied recorded telemetry without synthesizing replacement data."""
    if upload is not None:
        raw = upload.getvalue() if hasattr(upload, "getvalue") else upload
        return pd.read_csv(BytesIO(raw)), getattr(upload, "name", "Uploaded telemetry CSV")
    if path.exists():
        return pd.read_csv(path), path.name
    return pd.DataFrame(), "No telemetry file found"


def prepare_telemetry(raw: pd.DataFrame) -> dict[str, Any]:
    """Return measured data-quality counts and a parsed view of the source rows."""
    original_count = len(raw)
    frame = raw.copy()
    missing_by_field = frame.isna().sum().astype(int).to_dict() if not frame.empty else {}
    required_present = all(field in frame.columns for field in REQUIRED_TELEMETRY_FIELDS)
    if required_present:
        parsed_time = pd.to_datetime(frame["timestamp"], errors="coerce", utc=True)
        lat = pd.to_numeric(frame["gps_lat"], errors="coerce")
        lon = pd.to_numeric(frame["gps_lon"], errors="coerce")
        valid = parsed_time.notna() & lat.notna() & lon.notna()
        rejected_count = int((~valid).sum())
        frame["timestamp"] = parsed_time
        frame["gps_lat"] = lat
        frame["gps_lon"] = lon
        clean = frame.loc[valid].copy().sort_values("timestamp").reset_index(drop=True)
    else:
        rejected_count = original_count
        clean = frame.iloc[0:0].copy()
    for column in clean.columns:
        if column not in ("timestamp",):
            converted = pd.to_numeric(clean[column], errors="coerce")
            if converted.notna().any():
                clean[column] = converted
    duration = None
    if len(clean) > 1:
        duration = clean["timestamp"].iloc[-1] - clean["timestamp"].iloc[0]
    return {
        "raw": raw,
        "data": clean,
        "received": original_count,
        "processed": len(clean),
        "rejected": rejected_count,
        "missing_by_field": missing_by_field,
        "required_present": required_present,
        "duration": duration,
    }


def available_sensor_fields(frame: pd.DataFrame) -> list[str]:
    preferred = [field for field in (*KNOWN_SENSOR_FIELDS, "x", "y") if field in frame.columns]
    excluded = {"timestamp", "gps_lat", "gps_lon", *preferred}
    additional = [
        field for field in frame.columns
        if field not in excluded and pd.api.types.is_numeric_dtype(frame[field])
    ]
    return preferred + additional
