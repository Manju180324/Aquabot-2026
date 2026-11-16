from __future__ import annotations

from datetime import datetime
from uuid import uuid4

import streamlit as st


def set_mission_status(status: str, event: str | None = None) -> None:
    previous = st.session_state.mission_status
    mission_id = st.session_state.get("navigation_mission_id")
    from config.settings import NAVIGATION_MISSIONS_DB_PATH
    from services.navigation_log import NavigationMissionStore

    if (status == "Ready" and event == "Mission reset") or event == "Route position changed":
        if mission_id:
            store = NavigationMissionStore(NAVIGATION_MISSIONS_DB_PATH)
            store.finish_mission(mission_id, "Reset" if event == "Mission reset" else "Repositioned")
            store.close()
        st.session_state.navigation_mission_id = None
        st.session_state.navigation_logged_cursor = -1
        st.session_state.navigation_water_engine = None
    elif status in {"Stopped", "Complete"} and mission_id:
        store = NavigationMissionStore(NAVIGATION_MISSIONS_DB_PATH)
        store.finish_mission(mission_id, status)
        store.close()
        st.session_state.navigation_mission_id = None
        st.session_state.navigation_logged_cursor = -1
        st.session_state.navigation_water_engine = None

    if status == "Running" and st.session_state.get("navigation_mission_id") is None:
        mission_id = str(uuid4())
        st.session_state.navigation_mission_id = mission_id
        st.session_state.navigation_logged_cursor = -1
        st.session_state.navigation_water_engine = None
        store = NavigationMissionStore(NAVIGATION_MISSIONS_DB_PATH)
        store.create_mission(mission_id, st.session_state.get("telemetry_source", "recorded CSV"))
        store.close()

    if previous != status or event == "Route position changed":
        history = st.session_state.mission_history
        history.insert(0, {
            "Time": datetime.now().astimezone().isoformat(timespec="seconds"),
            "Event": event or f"{previous} → {status}",
            "Route point": int(st.session_state.mission_cursor) + 1,
        })
        del history[100:]
    st.session_state.mission_status = status
