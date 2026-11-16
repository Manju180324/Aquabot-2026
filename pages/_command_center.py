from __future__ import annotations

import pandas as pd
import streamlit as st

from components.ui import page_heading
from services.mission import set_mission_status
from services.telemetry import FIELD_LABELS, available_sensor_fields
from services.water_quality_simulation import WaterQualitySimulation
from visualizations.auv_scene import scene_html
from visualizations.navigation import navigation_figure


def _duration_label(duration) -> str:
    if duration is None or pd.isna(duration):
        return "—"
    seconds = int(duration.total_seconds())
    return f"{seconds // 60}m {seconds % 60:02d}s"


def render(context: dict) -> None:
    frame = context["telemetry"]["data"]
    page_heading("AQUABOT / NAVIGATION", "Navigation", "Navigation data")
    if frame.empty:
        st.warning("No usable telemetry rows are available. Upload a CSV with timestamp, gps_lat, and gps_lon columns in the sidebar.")
        return
    idx = max(0, min(int(st.session_state.mission_cursor), len(frame) - 1))
    row = frame.iloc[idx]
    duration_text = _duration_label(context["telemetry"].get("duration"))
    water_engine = st.session_state.get("navigation_water_engine")
    if water_engine is None:
        water_engine = WaterQualitySimulation()
        st.session_state.navigation_water_engine = water_engine
    if water_engine.run_id is None:
        water_engine.start_run("navigation-water-quality")
    lon_span = max(float(frame["gps_lon"].max() - frame["gps_lon"].min()), 1e-12)
    lat_span = max(float(frame["gps_lat"].max() - frame["gps_lat"].min()), 1e-12)
    grid_x = (float(row["gps_lon"]) - float(frame["gps_lon"].min())) / lon_span * (water_engine.width - 1)
    grid_y = (float(row["gps_lat"]) - float(frame["gps_lat"].min())) / lat_span * (water_engine.height - 1)
    water_values = water_engine.read_cell(round(grid_x), round(grid_y))
    st.session_state.navigation_water_values = water_values
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("pH (sim)", f"{water_values['ph']:.2f}", help="Simulated reading at the current route location.")
    c2.metric("Turbidity (sim)", f"{water_values['turbidity']:.2f}", help="Simulated reading at the current route location.")
    c3.metric("Salinity (sim)", f"{water_values['salinity']:.2f}", help="Simulated reading at the current route location.")
    c4.metric("Mission duration", duration_text, "From first to last valid timestamp")
    st.markdown(scene_html(frame, idx), unsafe_allow_html=True)
    left, right = st.columns([1.7, 1])
    with left:
        st.markdown("#### Navigation · GPS track")
        st.plotly_chart(navigation_figure(frame, idx), width="stretch", key="command_route")
    with right:
        st.markdown("#### Vehicle status")
        status_label = "PLAYBACK · " + st.session_state.mission_status.upper()
        st.markdown(f'<div class="panel"><span class="status-pill"><span class="status-dot"></span>{status_label}</span><p style="margin:18px 0 6px;color:#8fb2c4">CURRENT COORDINATE</p><div style="font:500 16px \'DM Mono\',monospace">{row["gps_lat"]:.6f}° N<br>{row["gps_lon"]:.6f}° E</div><p style="margin:18px 0 4px;color:#8fb2c4">DESTINATION · RECORDED ROUTE END</p><div style="font:500 14px \'DM Mono\',monospace">{frame["gps_lat"].iloc[-1]:.6f}, {frame["gps_lon"].iloc[-1]:.6f}</div></div>', unsafe_allow_html=True)
        st.markdown("##### Mission controls")
        b1, b2 = st.columns(2)
        if b1.button("▶ Start / Resume", width="stretch", key="cmd_start"):
            if st.session_state.mission_status in ("Ready", "Stopped", "Complete") and st.session_state.mission_cursor >= len(frame) - 1:
                st.session_state.mission_cursor = 0
            set_mission_status("Running")
            st.session_state.mission_last_tick = 0.0
            st.rerun()
        if b2.button("Ⅱ Pause", width="stretch", key="cmd_pause"):
            set_mission_status("Paused")
            st.rerun()
        b3, b4 = st.columns(2)
        if b3.button("■ Stop", width="stretch", key="cmd_stop"):
            set_mission_status("Stopped")
            st.rerun()
        if b4.button("↻ Reset", width="stretch", key="cmd_reset"):
            set_mission_status("Ready", "Mission reset")
            st.session_state.mission_cursor = 0
            st.rerun()
        slider_key = f"command_route_scrub_{idx}"
        slider_value = st.slider("Recorded route scrubber", 0, len(frame) - 1, idx, key=slider_key)
        if slider_value != idx:
            st.session_state.mission_cursor = slider_value
            set_mission_status("Paused", "Route position changed")
            st.rerun()
    st.markdown("#### Sensor telemetry")
    sensor_fields = [
        field for field in available_sensor_fields(frame)
        if field not in {"speed", "lora_rssi"}
    ]
    if not sensor_fields:
        st.info("No supported sensor fields are present beyond the GPS track.")
    else:
        columns = st.columns(min(4, len(sensor_fields)))
        for number, field in enumerate(sensor_fields):
            value = row.get(field)
            label, unit = FIELD_LABELS.get(field, (field.replace("_", " ").title(), "CSV units unspecified"))
            with columns[number % len(columns)]:
                rendered = f"{value:.3f}" if pd.notna(value) else "—"
                st.markdown(f'<div class="sensor-card"><div class="sensor-name">{label}</div><div class="sensor-value">{rendered}</div><div class="sensor-unit">{unit} · recorded</div></div>', unsafe_allow_html=True)
    st.caption("Battery, depth, temperature, humidity, and physical sonar readings are not in the supplied CSV. No values are inferred for these fields.")
    if st.session_state.mission_history:
        with st.expander("Mission history"):
            st.dataframe(st.session_state.mission_history, width="stretch", hide_index=True)
