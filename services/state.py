from __future__ import annotations

import streamlit as st


def initialize_state() -> None:
    defaults = {
        "waste_counts": {"Plastic": 0, "Metallic": 0, "Biodegradable": 0},
        "detection_history": [],
        "vision_runs": [],
        "last_detection_key": None,
        "last_detection_result": None,
        "chat_history": [],
        "pdf_data": None,
        "navigation": {"direction": "Stop", "speed": 0.0, "auto_navigate": True},
        "sensor_sim": {"ultrasonic": 80.0, "roll": 0.0},
        "mission_status": "Ready",
        "mission_cursor": 0,
        "mission_started_at": None,
        "mission_history": [],
        "mission_last_tick": 0.0,
        "navigation_mission_id": None,
        "navigation_logged_cursor": -1,
        "navigation_water_engine": None,
        "water_engine": None,
        "water_status": "Ready",
        "water_history": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
