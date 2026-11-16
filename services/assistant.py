from __future__ import annotations

import json
import os

import pandas as pd


def summarize_dashboard_data(
    frame: pd.DataFrame,
    received_rows: int,
    waste_counts: dict[str, int],
    mission_status: str,
    mission_cursor: int,
    water_quality_values: dict[str, float] | None = None,
) -> str:
    sensor_summary = {}
    for field in ("speed", "ultrasonic", "lora_rssi", "lora_snr"):
        if field not in frame.columns:
            continue
        values = pd.to_numeric(frame[field], errors="coerce").dropna()
        if not values.empty:
            sensor_summary[field] = {
                "minimum": round(float(values.min()), 3),
                "average": round(float(values.mean()), 3),
                "maximum": round(float(values.max()), 3),
            }

    return json.dumps({
        "telemetry": {
            "received_rows": int(received_rows),
            "valid_route_rows": int(len(frame)),
            "available_non_location_fields": [
                field for field in frame.columns
                if field not in {"gps_lat", "gps_lon"}
            ],
            "sensor_summary": sensor_summary,
        },
        "waste_detection_counts": waste_counts,
        "navigation_playback": {
            "status": mission_status,
            "current_point": int(mission_cursor) + 1 if len(frame) else None,
            "total_points": int(len(frame)),
        },
        "current_simulated_water_quality": water_quality_values,
        "privacy_note": "Raw CSV rows and GPS coordinates are not included.",
    }, ensure_ascii=True)


def ask_aquabot(
    query: str,
    counts: dict[str, int],
    dashboard_context: str = "",
) -> str:
    """Use the optional Groq chat integration; never expose or log the API key."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return "AquaBot Assistant is not connected: GROQ_API_KEY is not configured. Detection and dashboard features remain available."
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_groq import ChatGroq
    except ImportError:
        return "AquaBot Assistant is unavailable because its optional LangChain packages are not installed."
    model = ChatGroq(groq_api_key=api_key, model_name="llama-3.1-8b-instant", temperature=0.4)
    system = (
        "You are AquaBot, the assistant for this aquatic monitoring dashboard. "
        "Answer questions using only the supplied dashboard summary; if it does not contain the answer, say so. "
        "Keep replies concise, distinguish recorded telemetry from simulated water-quality values, "
        "and never claim the boat is connected to live hardware. "
        "The summary intentionally excludes raw CSV rows and GPS coordinates. "
        "Waste detection counts: "
        + ", ".join(f"{name}={value}" for name, value in counts.items())
        + "\nDashboard summary: "
        + dashboard_context
    )
    try:
        result = model.invoke([SystemMessage(content=system), HumanMessage(content=query)])
        return str(result.content)
    except Exception as exc:
        return f"The assistant request failed ({type(exc).__name__}). Check the optional LLM connection and try again."
