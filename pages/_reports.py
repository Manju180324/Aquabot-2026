from __future__ import annotations

import streamlit as st

from components.ui import page_heading
from config.settings import NAVIGATION_MISSIONS_DB_PATH
from services.navigation_log import NavigationMissionStore
from services.reports import make_detection_pdf, make_navigation_pdf


def render(context: dict) -> None:
    page_heading("AQUABOT / MISSION REPORT", "Mission reports", "Browse saved navigation movement logs and waste detections from previous runs.")
    navigation_tab, detection_tab = st.tabs(["Navigation movement log", "Waste detection report"])

    with navigation_tab:
        store = NavigationMissionStore(NAVIGATION_MISSIONS_DB_PATH)
        missions = store.missions()
        if missions.empty:
            st.info("No navigation movement log has been recorded yet. Start route playback on Navigation animation. Each route point will be saved here.")
        else:
            choices = missions.to_dict("records")
            mission_by_label = {
                f"{item['started_at']} · {item['status']} · {int(item['movement_count']):,} points · {item['mission_id'][:8]}": item
                for item in choices
            }
            selected_label = st.selectbox("Navigation mission", list(mission_by_label), key="report_navigation_mission")
            mission = mission_by_label[selected_label]
            movements = store.movements(mission["mission_id"])
            a, b, c, d = st.columns(4)
            a.metric("Mission status", mission["status"])
            b.metric("Movement records", f"{len(movements):,}")
            c.metric("Source", mission["source_name"])
            d.metric("GPS points", f"{movements['gps_lat'].notna().sum():,}" if not movements.empty else "0")
            st.warning("GPS coordinates are taken from recorded telemetry. Water-grid X/Y and pH, turbidity, and salinity are freshly simulated for every route point; they are not physical sensor measurements.")
            if not movements.empty:
                st.dataframe(movements, width="stretch", hide_index=True)
                csv_bytes = movements.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Download movement log CSV",
                    data=csv_bytes,
                    file_name=f"aquabot_mission_{mission['mission_id'][:8]}_movements.csv",
                    mime="text/csv",
                    key="download_navigation_csv",
                )
                if st.button("Generate navigation PDF", key="generate_navigation_pdf"):
                    st.session_state.navigation_pdf_data = make_navigation_pdf(mission, movements)
                if st.session_state.get("navigation_pdf_data"):
                    st.download_button(
                        "Download navigation PDF",
                        data=st.session_state.navigation_pdf_data,
                        file_name=f"aquabot_mission_{mission['mission_id'][:8]}.pdf",
                        mime="application/pdf",
                        key="download_navigation_pdf",
                    )
            else:
                st.caption("This mission has no route-point records yet. Records are written as playback advances.")
        store.close()

    with detection_tab:
        st.markdown("#### Camera detection totals")
        st.write(st.session_state.waste_counts)
        if st.session_state.detection_history:
            st.dataframe(st.session_state.detection_history, width="stretch", hide_index=True)
        else:
            st.info("No detections have been recorded in this Streamlit session.")
        if st.button("Generate waste detection PDF", key="generate_detection_pdf"):
            st.session_state.pdf_data = make_detection_pdf(st.session_state.detection_history, st.session_state.waste_counts)
        if st.session_state.pdf_data:
            st.download_button("Download waste detection PDF", data=st.session_state.pdf_data, file_name="aquabot_detection_report.pdf", mime="application/pdf")
        elif st.session_state.detection_history:
            st.caption("PDF generation requires the optional fpdf package.")
