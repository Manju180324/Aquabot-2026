from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import random

import numpy as np
import streamlit as st

from components.ui import page_heading
from config.settings import NAVIGATION_MISSIONS_DB_PATH
from services.anomaly_detection import ANOMALY_BIAS, ANOMALY_THRESHOLD, ANOMALY_WEIGHTS, threshold_anomalies
from services.navigation_log import NavigationMissionStore
from services.waste_detection import detect_image, update_autonomous_navigation
from visualizations.anomalies import anomaly_locations_figure


def render(context: dict) -> None:
    page_heading("AQUABOT / VISION SYSTEM", "Waste detection data", "Run camera or uploaded frames through the included YOLO weights, then review detections, session totals, confidence, and inference time. No boat-control link is configured.")
    model_name = st.selectbox("YOLO weights", ["yolov8x.pt", "yolov8m.pt", "yolov8n.pt"], help="Larger variants generally use more compute. The weights included with this project are used.")
    camera, upload = st.tabs(["Camera", "Upload image"])
    image_file = None
    with camera:
        image_file = st.camera_input("Capture a frame", key="aquabot_camera")
    with upload:
        uploaded = st.file_uploader("Choose an image", type=["png", "jpg", "jpeg"], key="vision_upload")
        if uploaded is not None:
            image_file = uploaded
    if image_file is not None:
        try:
            image_bytes = image_file.getvalue()
            detection_key = sha256(model_name.encode() + image_bytes).hexdigest()
            is_new_frame = detection_key != st.session_state.last_detection_key
            if is_new_frame:
                result = detect_image(image_bytes, model_name)
                st.session_state.last_detection_key = detection_key
                st.session_state.last_detection_result = result
                st.session_state.vision_runs.append({"Time": datetime.now().astimezone().isoformat(timespec="seconds"), "Inference ms": round(result["elapsed_ms"], 2), "Detections": len(result["detections"]), "Model": model_name})
                st.session_state.vision_runs[:] = st.session_state.vision_runs[-200:]
            else:
                result = st.session_state.last_detection_result
            left, right = st.columns([1.55, 1])
            with left:
                st.image(result["annotated"], caption="YOLO annotated frame", width="stretch")
            with right:
                best = result["best"]
                if best:
                    st.metric("Waste class", best["waste"])
                    st.metric("YOLO label", best["label"])
                    st.metric("Confidence", f"{best['confidence']:.2%}")
                    st.metric("Measured inference", f"{result['elapsed_ms']:.1f} ms")
                    st.metric("Horizontal target", best["box_position"].title())
                    if is_new_frame:
                        update_autonomous_navigation(best["box_position"])
                        ratio = best["bbox_height"] / max(best["frame_height"], 1)
                        st.session_state.sensor_sim["ultrasonic"] = round(float(np.clip(150 * (1 - ratio), 20, 150)), 1)
                else:
                    st.info("No non-living object was detected in this frame.")
                    if is_new_frame:
                        update_autonomous_navigation(None)
                sensor = st.session_state.sensor_sim
                if is_new_frame:
                    sensor["roll"] += random.uniform(-0.4, 0.4)
                st.metric("Image-size distance proxy", f"{sensor['ultrasonic']:.1f}", "SIMULATED · not an ultrasonic reading")
                st.metric("Roll drift", f"{sensor['roll']:.1f}°", "SIMULATED")
                st.metric("Navigation suggestion", st.session_state.navigation["direction"], f"speed factor {st.session_state.navigation['speed']:.1f}")
            best = result["best"]
            if best and is_new_frame:
                key = best["waste"]
                st.session_state.waste_counts[key] = st.session_state.waste_counts.get(key, 0) + 1
                st.session_state.detection_history.append({"Time": datetime.now().astimezone().isoformat(timespec="seconds"), "Waste": best["waste"], "YOLO label": best["label"], "Confidence": round(best["confidence"], 3), "Target position": best["box_position"], "Inference ms": round(result["elapsed_ms"], 2)})
            st.caption(f"Non-living objects detected in frame: {len(result['detections'])}. Material class is a heuristic mapping of generic YOLO labels, not a dedicated waste-trained classifier.")
        except Exception as exc:
            st.error(f"Detection could not run: {exc}")
            st.info("Confirm the selected YOLO weights exist and the optional OpenCV/Ultralytics dependencies are installed.")
    st.markdown("#### Session detection totals")
    cols = st.columns(3)
    for column, (name, count) in zip(cols, st.session_state.waste_counts.items()):
        column.metric(name, count)
    if st.session_state.detection_history:
        st.dataframe(st.session_state.detection_history[-30:], width="stretch", hide_index=True)

    st.divider()
    st.markdown("#### Water-quality anomaly coordinates")
    w1, w2, w3 = ANOMALY_WEIGHTS
    st.markdown(
        f"Raw weighted deviation: $R = {w1:.2f}|z_{{pH}}| + {w2:.2f}|z_{{turbidity}}| + "
        f"{w3:.2f}|z_{{salinity}}| + {ANOMALY_BIAS:.2f}$. "
        f"Bounded composite score: $S = R/(1+R)$, so $0 \\le S < 1$. "
        f"Flag route points where $S > {ANOMALY_THRESHOLD:.2f}$. The z-scores use the simulation run's baseline statistics."
    )
    st.warning("GPS coordinates are recorded route data. pH, turbidity, salinity, and their composite scores come from the simulated water-quality model because these sensors are absent from the supplied GPS CSV.")
    mission_store = NavigationMissionStore(NAVIGATION_MISSIONS_DB_PATH)
    mission_options = mission_store.missions()
    mission_options = mission_options.loc[mission_options["movement_count"] > 0] if not mission_options.empty else mission_options
    if mission_options.empty:
        st.info("No saved route chemistry readings yet. Start playback in Navigation animation; this page will show above-threshold coordinates as each point is logged.")
    else:
        mission_rows = mission_options.to_dict("records")
        mission_labels = {
            f"{row['started_at']} · {int(row['movement_count']):,} points · {row['mission_id'][:8]}": row["mission_id"]
            for row in mission_rows
        }
        selected_label = st.selectbox("Navigation mission", list(mission_labels), key="waste_anomaly_mission")
        movement_rows = mission_store.movements(mission_labels[selected_label])
        flagged = threshold_anomalies(movement_rows, ANOMALY_THRESHOLD)
        total, count, peak = st.columns(3)
        total.metric("Movement samples", f"{len(movement_rows):,}")
        count.metric("Above-threshold coordinates", f"{len(flagged):,}", f"score > {ANOMALY_THRESHOLD:.2f}")
        peak.metric("Highest composite score", f"{movement_rows['anomaly_index'].max():.3f}" if not movement_rows.empty else "—")
        st.plotly_chart(anomaly_locations_figure(movement_rows, flagged, ANOMALY_THRESHOLD), width="stretch", key="waste_anomaly_locations")
        if not flagged.empty:
            display_columns = ["route_index", "recorded_at", "gps_lat", "gps_lon", "water_grid_x", "water_grid_y", "ph", "turbidity", "salinity", "anomaly_score", "water_quality_source"]
            st.dataframe(
                flagged[display_columns],
                width="stretch",
                hide_index=True,
                column_config={
                    "route_index": st.column_config.NumberColumn("Route point", format="%d"),
                    "recorded_at": st.column_config.TextColumn("Recorded at"),
                    "gps_lat": st.column_config.NumberColumn("GPS latitude", format="%.6f"),
                    "gps_lon": st.column_config.NumberColumn("GPS longitude", format="%.6f"),
                    "water_grid_x": st.column_config.NumberColumn("Water grid X", format="%.2f"),
                    "water_grid_y": st.column_config.NumberColumn("Water grid Y", format="%.2f"),
                    "ph": st.column_config.NumberColumn("pH (sim)", format="%.3f"),
                    "turbidity": st.column_config.NumberColumn("Turbidity (sim)", format="%.3f"),
                    "salinity": st.column_config.NumberColumn("Salinity (sim)", format="%.3f"),
                    "anomaly_score": st.column_config.NumberColumn("Composite score", format="%.3f"),
                    "water_quality_source": st.column_config.TextColumn("Reading source"),
                },
            )
            st.download_button(
                "Download above-threshold coordinates CSV",
                data=flagged[display_columns].to_csv(index=False).encode("utf-8"),
                file_name=f"aquabot_anomaly_coordinates_{mission_labels[selected_label][:8]}.csv",
                mime="text/csv",
                key="download_anomaly_coordinates",
            )
        else:
            st.success(f"No logged simulated chemistry point in this mission has a composite score above {ANOMALY_THRESHOLD:.2f}.")
    mission_store.close()
