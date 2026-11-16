from __future__ import annotations

import streamlit as st

from components.ui import page_heading
from services.processing import pipeline_stages


def render(context: dict) -> None:
    telemetry = context["telemetry"]
    frames = st.session_state.vision_runs
    stages = pipeline_stages(telemetry, len(frames))
    page_heading("AQUABOT / DATA PIPELINE", "Processing pipeline", "Counts below are computed from the loaded CSV or this session's camera runs. Unavailable stages are called out instead of estimated.")
    cols = st.columns(4)
    for index, stage in enumerate(stages):
        state = stage["state"]
        cls = "active" if state == "complete" else "pending"
        color = "#65ead3" if state == "complete" else "#f4c27a" if state == "warning" else "#8ca8b7"
        with cols[index % 4]:
            st.markdown(f'<div class="pipeline-stage {cls}"><div class="eyebrow">{index + 1:02d} / 08</div><div style="font-weight:800;margin:7px 0">{stage["stage"]}</div><span style="color:{color};font:11px \'DM Mono\',monospace">● {state.upper()}</span><div style="margin-top:10px;color:#a6c2d0;font-size:12px">Received {stage["received"]:,}<br>Processed {stage["processed"]:,}<br>Rejected {stage["rejected"]:,}</div></div>', unsafe_allow_html=True)
        if index < len(stages) - 1:
            with cols[index % 4]:
                st.progress(1.0 if state == "complete" else 0.0)
    st.markdown("#### Inspect a stage")
    selected_name = st.selectbox("Pipeline stage", [item["stage"] for item in stages])
    stage = next(item for item in stages if item["stage"] == selected_name)
    st.markdown(f'<div class="panel"><div class="eyebrow">{stage["state"].upper()}</div><h3>{stage["stage"]}</h3><p style="color:#a6c2d0">{stage["evidence"]}</p><p style="font:12px \'DM Mono\',monospace;color:#69dce2">Received {stage["received"]:,} &nbsp;·&nbsp; Processed {stage["processed"]:,} &nbsp;·&nbsp; Rejected {stage["rejected"]:,}</p></div>', unsafe_allow_html=True)
    st.caption("Processing durations are not instrumented by the existing implementations, so the dashboard does not report fabricated timings.")
    st.markdown("#### Vision processing · session evidence")
    total_ms = sum(float(item.get("Inference ms", 0)) for item in frames)
    average_ms = total_ms / len(frames) if frames else None
    a, b, c = st.columns(3)
    a.metric("Camera frames processed", len(frames))
    b.metric("Measured mean inference", f"{average_ms:.1f} ms" if average_ms is not None else "Not available")
    c.metric("Waste-class records", sum(st.session_state.waste_counts.values()))
    st.caption("Inference timing is measured in this running session only. CSV anomaly detection is not implemented; water-quality anomaly scores are available on the separate simulation page.")
