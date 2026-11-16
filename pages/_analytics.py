from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from components.ui import page_heading
from config.settings import WATER_QUALITY_DB_PATH
from services.processing import pipeline_stages
from services.telemetry import FIELD_LABELS, available_sensor_fields
from services.water_quality_simulation import WaterQualitySimulation
from visualizations.charts import sensor_trend
from visualizations.water_quality import history_figure, simulation_figure


def _get_water_engine() -> WaterQualitySimulation:
    engine = st.session_state.get("water_engine")
    if engine is None:
        WATER_QUALITY_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        engine = WaterQualitySimulation(db_path=Path(WATER_QUALITY_DB_PATH))
        st.session_state.water_engine = engine
    return engine


def _render_recorded_sensors(data: dict) -> None:
    frame = data["data"]
    if frame.empty:
        st.warning("No usable telemetry rows are loaded. Upload a CSV with timestamp, gps_lat, and gps_lon columns in the sidebar.")
        return

    fields = available_sensor_fields(frame)
    start_date, end_date = frame["timestamp"].min().date(), frame["timestamp"].max().date()
    selected_range = st.date_input("Recording date range", value=(start_date, end_date), key="sensor_date_range")
    filtered = frame
    if isinstance(selected_range, tuple) and len(selected_range) == 2:
        start = pd.Timestamp(selected_range[0], tz="UTC")
        end = pd.Timestamp(selected_range[1], tz="UTC") + pd.Timedelta(days=1)
        filtered = frame.loc[(frame["timestamp"] >= start) & (frame["timestamp"] < end)]
    if filtered.empty:
        st.warning("No telemetry rows fall within the selected dates.")
        return

    intervals = filtered["timestamp"].diff().dt.total_seconds().dropna()
    median_interval = float(intervals.median()) if not intervals.empty else None
    duration = filtered["timestamp"].iloc[-1] - filtered["timestamp"].iloc[0]
    duration_seconds = duration.total_seconds()
    sample_rate = (len(filtered) - 1) * 60 / duration_seconds if duration_seconds > 0 else None
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Telemetry source", "Recorded CSV")
    k2.metric("Rows in view", f"{len(filtered):,}")
    k3.metric("Median sample interval", f"{median_interval:.3f} s" if median_interval is not None else "Not available")
    k4.metric("Collection rate", f"{sample_rate:.1f} rows/min" if sample_rate is not None else "Not available")

    latest = filtered.iloc[-1]
    st.markdown("#### Latest recorded sensor values")
    card_fields = [*fields, "gps_lat", "gps_lon"]
    cards = st.columns(min(4, len(card_fields)))
    for index, field in enumerate(card_fields):
        value = latest.get(field)
        label, unit = FIELD_LABELS.get(field, (field.replace("_", " ").title(), "CSV units unspecified"))
        if pd.isna(value):
            rendered = "—"
        elif field in ("gps_lat", "gps_lon"):
            rendered = f"{value:.6f}"
        else:
            rendered = f"{value:.3f}"
        with cards[index % len(cards)]:
            st.markdown(f'<div class="sensor-card"><div class="sensor-name">{label}</div><div class="sensor-value">{rendered}</div><div class="sensor-unit">{unit} · recorded</div></div>', unsafe_allow_html=True)

    st.markdown("#### Sensor history")
    if fields:
        selected_fields = st.multiselect(
            "Fields to chart",
            fields,
            default=fields,
            format_func=lambda key: FIELD_LABELS.get(key, (key.replace("_", " ").title(), ""))[0],
            key="sensor_chart_fields",
        )
        for offset in range(0, len(selected_fields), 2):
            chart_columns = st.columns(2)
            for col, field in zip(chart_columns, selected_fields[offset:offset + 2]):
                with col:
                    st.plotly_chart(sensor_trend(filtered, field), width="stretch", key=f"sensor_history_{field}")

        numeric_fields = [field for field in fields if pd.api.types.is_numeric_dtype(filtered[field]) and filtered[field].nunique(dropna=True) > 1]
        if len(numeric_fields) >= 2:
            st.markdown("#### Sensor-wise comparison")
            x_col, y_col = st.columns(2)
            x_field = x_col.selectbox("X axis", numeric_fields, key="sensor_compare_x")
            y_field = y_col.selectbox("Y axis", [field for field in numeric_fields if field != x_field], key="sensor_compare_y")
            fig = px.scatter(
                filtered,
                x=x_field,
                y=y_field,
                color="speed" if "speed" in filtered.columns and x_field != "speed" and y_field != "speed" else None,
                hover_data=["timestamp"],
                template="plotly_dark",
                opacity=0.68,
                color_continuous_scale=["#287fac", "#62eee0"],
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#071c2b", height=340, margin=dict(l=8, r=8, t=10, b=8))
            st.plotly_chart(fig, width="stretch")

    st.markdown("#### Recorded data quality")
    missing = pd.Series(data["missing_by_field"], name="Missing values", dtype="int64")
    q1, q2, q3 = st.columns(3)
    q1.metric("Source rows", f"{data['received']:,}")
    q2.metric("Valid rows", f"{data['processed']:,}")
    q3.metric("Rejected route rows", f"{data['rejected']:,}", "Invalid timestamp or GPS")
    if not missing.empty:
        missing_rows = missing[missing > 0].rename_axis("Field").reset_index()
        if missing_rows.empty:
            st.success("No missing values were found in the supplied CSV fields.")
        else:
            st.dataframe(missing_rows, width="stretch", hide_index=True)
    st.info("No configured battery, depth, temperature, signal, or navigation thresholds exist for this CSV. No sensor alarms or units are inferred.")
    with st.expander("Inspect collected telemetry rows"):
        st.dataframe(filtered, width="stretch", hide_index=True)
        st.download_button("Download filtered telemetry CSV", filtered.to_csv(index=False).encode("utf-8"), "aquabot_filtered_telemetry.csv", "text/csv")


def _render_water_quality_simulation() -> None:
    st.markdown('<div class="hero"><div class="eyebrow">SIMULATION · NOT LIVE SENSOR DATA</div><h3 style="margin:8px 0 4px">Water-quality patrol analytics</h3><span style="color:#9bb9c8">pH, turbidity, salinity, movement, and anomaly scores come from the separate grid simulation ported from the Tkinter engine.</span></div>', unsafe_allow_html=True)
    engine = _get_water_engine()
    controls = st.columns(4)
    if controls[0].button("▶ Start / Resume", key="analytics_water_start", width="stretch"):
        if engine.run_id is None or st.session_state.water_status in ("Ready", "Stopped"):
            engine.start_run("streamlit-water-quality")
            st.session_state.water_history = []
        st.session_state.water_status = "Running"
        st.rerun()
    if controls[1].button("Ⅱ Pause", key="analytics_water_pause", width="stretch"):
        st.session_state.water_status = "Paused"
        st.rerun()
    if controls[2].button("■ Stop", key="analytics_water_stop", width="stretch"):
        st.session_state.water_status = "Stopped"
        st.rerun()
    if controls[3].button("↻ Reset", key="analytics_water_reset", width="stretch"):
        if engine.db is not None:
            engine.db.close()
        st.session_state.water_engine = WaterQualitySimulation(db_path=Path(WATER_QUALITY_DB_PATH))
        st.session_state.water_history = []
        st.session_state.water_status = "Ready"
        st.rerun()

    history = st.session_state.water_history
    x, y = engine.robot.position
    left, right = st.columns([1.5, 1])
    with left:
        st.plotly_chart(simulation_figure(engine.grid, history, (x, y), engine.robot.heading), width="stretch", key="analytics_water_grid")
    with right:
        st.markdown("#### Simulation status")
        st.metric("Status", st.session_state.water_status)
        st.metric("Patrol mode", engine.robot.mode if history else "Patrolling")
        st.metric("Simulation samples", len(history))
        if history:
            latest = history[-1]
            st.metric("Composite anomaly", f"{latest['anomaly_index']:.2f}", f"run threshold {latest['anomaly_threshold']:.2f}")
            s1, s2, s3 = st.columns(3)
            s1.metric("pH", f"{latest['ph']:.2f}", "simulated")
            s2.metric("Turbidity", f"{latest['turbidity']:.2f}", "simulated")
            s3.metric("Salinity", f"{latest['salinity']:.2f}", "simulated")
        else:
            st.info("Start the patrol to collect this run's simulated sensor history.")
    if history:
        st.markdown("#### Collected simulation readings")
        st.plotly_chart(history_figure(history), width="stretch", key="analytics_water_history")
        simulated_alerts = [sample for sample in history if sample["anomaly_index"] > sample["anomaly_threshold"]]
        st.caption(f"{len(simulated_alerts)} simulated sample(s) crossed the run-derived baseline threshold. This is separate from recorded boat telemetry.")
        with st.expander("Inspect simulated sensor samples"):
            st.dataframe(pd.DataFrame(history), width="stretch", hide_index=True)


def _render_pipeline_summary(data: dict) -> None:
    stages = pipeline_stages(data, len(st.session_state.vision_runs))
    st.markdown("#### Ingestion and processing summary")
    columns = st.columns(4)
    for index, stage in enumerate(stages):
        color = "#65ead3" if stage["state"] == "complete" else "#f4c27a" if stage["state"] == "warning" else "#8ca8b7"
        with columns[index % 4]:
            st.markdown(f'<div class="pipeline-stage"><div class="eyebrow">{index + 1:02d} / 08</div><div style="font-weight:800;margin:7px 0">{stage["stage"]}</div><span style="color:{color};font:11px \'DM Mono\',monospace">● {stage["state"].upper()}</span><div style="margin-top:10px;color:#a6c2d0;font-size:12px">Received {stage["received"]:,}<br>Processed {stage["processed"]:,}<br>Rejected {stage["rejected"]:,}</div></div>', unsafe_allow_html=True)
    stage_name = st.selectbox("Inspect a stage", [item["stage"] for item in stages], key="analytics_pipeline_stage")
    stage = next(item for item in stages if item["stage"] == stage_name)
    st.info(stage["evidence"])
    left, right = st.columns(2)
    left.metric("Camera frames processed", len(st.session_state.vision_runs))
    inference_times = [float(item.get("Inference ms", 0)) for item in st.session_state.vision_runs]
    right.metric("Mean YOLO inference", f"{sum(inference_times) / len(inference_times):.1f} ms" if inference_times else "Not available")
    st.caption("Pipeline stage timings and recorded-CSV anomaly detection are not implemented. Camera inference duration is measured by this session; unavailable values are not fabricated.")


def render(context: dict) -> None:
    page_heading("AQUABOT / ANALYTICS", "Sensors & analytics", "Browse every supplied telemetry field, inspect recorded sensor history, and review the separate water-quality simulation.")
    data = context["telemetry"]
    recorded_tab, water_tab, pipeline_tab = st.tabs(["Recorded sensors", "Water-quality simulation", "Pipeline & data quality"])
    with recorded_tab:
        _render_recorded_sensors(data)
    with water_tab:
        _render_water_quality_simulation()
    with pipeline_tab:
        _render_pipeline_summary(data)
