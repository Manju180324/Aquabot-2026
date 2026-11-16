from __future__ import annotations

import time

import pandas as pd
import streamlit as st

from components.styles import inject_styles
from config.settings import APP_DIR, APP_TITLE, NAVIGATION_MISSIONS_DB_PATH
from pages import (
    _assistant as assistant,
    _command_center as command_center,
    _reports as reports,
    _waste_detection as waste_detection,
)
from services.state import initialize_state
from services.telemetry import load_telemetry, prepare_telemetry
from services.mission import set_mission_status
from services.navigation_log import NavigationMissionStore, record_route_range
from services.water_quality_simulation import WaterQualitySimulation


st.set_page_config(page_title=APP_TITLE, page_icon="🌊", layout="wide", initial_sidebar_state="expanded")
page_context = {}
pages = [
    st.Page(lambda: command_center.render(page_context), title="Navigation", icon="🧭", url_path="navigation", default=True),
    st.Page(lambda: waste_detection.render(page_context), title="Waste detection data", icon="🔍", url_path="waste-detection"),
    st.Page(lambda: reports.render(page_context), title="Mission reports", icon="📄", url_path="mission-reports"),
]
current_page = st.navigation(pages, position="sidebar")
initialize_state()
inject_styles()

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

with st.sidebar:
    st.image(str(APP_DIR / "assets" / "aquabot.svg"), width=62)
    st.markdown('<div class="eyebrow">AQUABOT INTELLIGENCE</div><h2 style="margin:5px 0 2px">AquaBot<br>Assistant</h2>', unsafe_allow_html=True)
    st.divider()
    upload = st.file_uploader("Upload telemetry CSV", type=["csv"], help="Expected route fields: timestamp, gps_lat, gps_lon. Existing sensor fields are used when present.")
    try:
        raw, source_name = load_telemetry(upload)
        telemetry = prepare_telemetry(raw)
        load_error = None
    except Exception as exc:
        raw, source_name = None, "Telemetry unavailable"
        telemetry = prepare_telemetry(pd.DataFrame())
        load_error = f"Could not read the selected telemetry: {exc}"
    if load_error:
        st.error(load_error)
    st.session_state.playback_increment = 5
    assistant.render_sidebar({"telemetry": telemetry})
    st.divider()
    st.markdown("**Instrument availability**")
    st.caption("Navigation · Waste detection data · Mission reports")
    st.caption("Simulated pH · turbidity · salinity\n\nBattery · depth · temperature · humidity: not provided")
    st.caption("AquaBot answers are based on summarized dashboard data.")

page_context.update({"telemetry": telemetry, "source": source_name})
st.session_state.telemetry_source = source_name

# Recorded route playback and the water-quality simulation advance independently.
active_playback = st.session_state.mission_status == "Running" and telemetry["processed"] > 0
active_water_simulation = st.session_state.water_status == "Running"
if active_playback or active_water_simulation:
    try:
        from streamlit_autorefresh import st_autorefresh

        st_autorefresh(interval=500, limit=None, key="aquabot_refresh")
        now = time.monotonic()
        if active_playback and now - st.session_state.get("mission_last_tick", 0.0) >= 0.45:
            next_index = st.session_state.mission_cursor + st.session_state.playback_increment
            mission_id = st.session_state.get("navigation_mission_id")
            if mission_id is None:
                # Handles playback resumed after a manual route reposition.
                set_mission_status("Running")
                mission_id = st.session_state.navigation_mission_id
            water_engine = st.session_state.get("navigation_water_engine")
            if water_engine is None:
                water_engine = WaterQualitySimulation()
                water_engine.start_run(f"navigation-{mission_id}")
                st.session_state.navigation_water_engine = water_engine
            store = NavigationMissionStore(NAVIGATION_MISSIONS_DB_PATH)
            store.create_mission(mission_id, source_name)
            first_unlogged = int(st.session_state.navigation_logged_cursor) + 1
            last_to_log = min(next_index, telemetry["processed"] - 1)
            record_route_range(store, mission_id, telemetry["data"], first_unlogged, last_to_log, water_engine)
            st.session_state.navigation_logged_cursor = max(first_unlogged - 1, last_to_log)
            store.close()
            if next_index >= telemetry["processed"] - 1:
                st.session_state.mission_cursor = telemetry["processed"] - 1
                set_mission_status("Complete")
            else:
                st.session_state.mission_cursor = next_index
            st.session_state.mission_last_tick = now
        if active_water_simulation:
            engine = st.session_state.get("water_engine")
            if engine is not None and engine.run_id is not None:
                sample = engine.step()
                st.session_state.water_history.append(sample)
                st.session_state.water_last_tick = now
    except ImportError:
        st.warning("Automatic playback refresh is unavailable. Install streamlit-autorefresh; mission controls and recorded route scrubbing still work.")

st.markdown('<div class="status-pill"><span class="status-dot"></span>DATA MODE · RECORDED TELEMETRY &amp; SIMULATION</div>', unsafe_allow_html=True)
current_page.run()
