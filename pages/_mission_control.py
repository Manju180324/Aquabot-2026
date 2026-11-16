from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from components.ui import page_heading
from config.settings import WATER_QUALITY_DB_PATH
from services.mission import set_mission_status
from services.water_quality_simulation import WaterQualitySimulation
from visualizations.navigation import navigation_figure
from visualizations.water_quality import history_figure, simulation_figure


def _get_water_engine() -> WaterQualitySimulation:
    engine = st.session_state.get("water_engine")
    if engine is None:
        WATER_QUALITY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        engine = WaterQualitySimulation(db_path=Path(WATER_QUALITY_DB_PATH))
        st.session_state.water_engine = engine
    return engine


def render(context: dict) -> None:
    page_heading("AQUABOT / MISSION CONTROL", "Mission operations", "Playback controls operate on recorded CSV telemetry; the water-quality patrol is a separate, explicitly simulated mission.")
    tab_route, tab_water = st.tabs(["Recorded navigation playback", "Water-quality simulation"])
    frame = context["telemetry"]["data"]
    with tab_route:
        if frame.empty:
            st.warning("Load valid telemetry to enable route playback.")
        else:
            idx = max(0, min(int(st.session_state.mission_cursor), len(frame) - 1))
            st.markdown(f'<span class="status-pill"><span class="status-dot"></span>PLAYBACK · {st.session_state.mission_status.upper()}</span>', unsafe_allow_html=True)
            progress = (idx + 1) / len(frame)
            st.progress(progress, text=f"Recorded route progress · {progress:.1%} · point {idx + 1:,} of {len(frame):,}")
            cols = st.columns(5)
            if cols[0].button("▶ Start", width="stretch"):
                set_mission_status("Running")
                st.session_state.mission_last_tick = 0.0
                st.rerun()
            if cols[1].button("Ⅱ Pause", width="stretch"):
                set_mission_status("Paused")
                st.rerun()
            if cols[2].button("↻ Resume", width="stretch"):
                set_mission_status("Running")
                st.session_state.mission_last_tick = 0.0
                st.rerun()
            if cols[3].button("■ Stop", width="stretch"):
                set_mission_status("Stopped")
                st.rerun()
            if cols[4].button("Reset", width="stretch"):
                st.session_state.mission_cursor = 0
                set_mission_status("Ready", "Mission reset")
                st.rerun()
            slider_key = f"mission_scrub_{idx}"
            slider_value = st.slider("Select recorded point", 0, max(0, len(frame) - 1), idx, key=slider_key)
            if slider_value != idx:
                st.session_state.mission_cursor = slider_value
                set_mission_status("Paused", "Route position changed")
                st.rerun()
            st.plotly_chart(navigation_figure(frame, idx), width="stretch", key="mission_route")
            current = frame.iloc[idx]
            a, b, c = st.columns(3)
            a.metric("Current waypoint", f"{idx + 1:,}")
            b.metric("GPS", f"{current['gps_lat']:.6f}, {current['gps_lon']:.6f}")
            c.metric("Speed", f"{current['speed']:.3f}" if "speed" in frame.columns and pd.notna(current.get("speed")) else "Not available", "CSV units unspecified")
            st.caption("Playback traverses the supplied recording; it does not send commands to a physical vehicle.")
            if st.session_state.mission_history:
                with st.expander("Mission history"):
                    st.dataframe(st.session_state.mission_history, width="stretch", hide_index=True)
    with tab_water:
        st.markdown('<div class="hero"><div class="eyebrow">SIMULATION · NOT LIVE SENSOR DATA</div><h3 style="margin:8px 0 4px">Water-quality patrol</h3><span style="color:#9bb9c8">Preserves the original grid, baseline sampling, composite anomaly scoring, and heuristic movement behavior.</span></div>', unsafe_allow_html=True)
        engine = _get_water_engine()
        controls = st.columns(4)
        if controls[0].button("▶ Start / Resume", key="water_start", width="stretch"):
            if engine.run_id is None or st.session_state.water_status in ("Ready", "Stopped"):
                engine.start_run("streamlit-water-quality")
                st.session_state.water_history = []
            st.session_state.water_status = "Running"
            st.rerun()
        if controls[1].button("Ⅱ Pause", key="water_pause", width="stretch"):
            st.session_state.water_status = "Paused"
            st.rerun()
        if controls[2].button("■ Stop", key="water_stop", width="stretch"):
            st.session_state.water_status = "Stopped"
            st.rerun()
        if controls[3].button("↻ Reset", key="water_reset", width="stretch"):
            if engine.db is not None:
                engine.db.close()
            engine = WaterQualitySimulation(db_path=Path(WATER_QUALITY_DB_PATH))
            st.session_state.water_engine = engine
            st.session_state.water_history = []
            st.session_state.water_status = "Ready"
            st.rerun()
        history = st.session_state.water_history
        px, py = engine.robot.position
        left, right = st.columns([1.5, 1])
        with left:
            st.plotly_chart(simulation_figure(engine.grid, history, (px, py), engine.robot.heading), width="stretch", key="water_map")
        with right:
            st.markdown("#### Simulated vehicle state")
            st.metric("Status", st.session_state.water_status)
            st.metric("Mode", engine.robot.mode if history else "Patrolling")
            st.metric("Position", f"({px:.2f}, {py:.2f})", "simulated grid coordinates")
            st.metric("Heading", f"{engine.robot.heading:.1f}°")
            if history:
                sample = history[-1]
                st.metric("Composite anomaly", f"{sample['anomaly_index']:.2f}", f"derived threshold {sample['anomaly_threshold']:.2f}")
                st.write(f"pH {sample['ph']:.2f} · Turbidity {sample['turbidity']:.2f} · Salinity {sample['salinity']:.2f}")
                st.caption("Threshold is computed from this simulation run's sampled baseline (95th percentile), matching the existing algorithm.")
            else:
                st.info("Start the simulation to establish the run baseline and begin sampling.")
        st.markdown("#### Simulated sensor history")
        st.plotly_chart(history_figure(history), width="stretch", key="water_history_chart")
        st.caption(f"Simulation samples persisted to local SQLite: {WATER_QUALITY_DB_PATH.name}. This source is intentionally separate from recorded boat telemetry.")
