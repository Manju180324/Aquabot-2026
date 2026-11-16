from __future__ import annotations

import streamlit as st

from components.ui import page_heading
from services.assistant import ask_aquabot, summarize_dashboard_data


def render_sidebar(context: dict) -> None:
    telemetry = context["telemetry"]
    history = st.session_state.chat_history
    st.markdown("#### Ask AquaBot")
    st.caption("Ask about telemetry, navigation, simulated water quality, and waste detections.")
    st.caption("Groq receives summarized dashboard data only; raw CSV rows and GPS coordinates are excluded.")
    query = st.chat_input("Ask about the dashboard…", key="sidebar_aquabot_chat")
    if query and query.strip():
        dashboard_context = summarize_dashboard_data(
            frame=telemetry["data"],
            received_rows=telemetry["received"],
            waste_counts=st.session_state.waste_counts,
            mission_status=st.session_state.mission_status,
            mission_cursor=st.session_state.mission_cursor,
            water_quality_values=st.session_state.get("navigation_water_values"),
        )
        with st.spinner("AquaBot is responding…"):
            answer = ask_aquabot(query.strip(), st.session_state.waste_counts, dashboard_context)
        history.append({"user": query.strip(), "bot": answer})

    for message in history[-6:]:
        with st.sidebar.chat_message("user"):
            st.write(message["user"])
        with st.sidebar.chat_message("assistant"):
            st.write(message["bot"])
    if not history:
        st.sidebar.info("Set GROQ_API_KEY locally to enable answers.")


def render(context: dict) -> None:
    page_heading("AQUABOT / ASSISTANT", "AquaBot assistant", "Optional Groq-powered marine robotics helper. The dashboard remains usable when the assistant is not configured.")
    st.markdown("Ask about the current detection totals, marine pollution, or the dashboard's recorded and simulated data sources.")
    with st.form("aquabot_chat_form", clear_on_submit=True):
        query = st.text_input("Message", placeholder="Ask a question about this mission…")
        submitted = st.form_submit_button("Send")
    if submitted and query.strip():
        with st.spinner("AquaBot is responding…"):
            answer = ask_aquabot(query.strip(), st.session_state.waste_counts)
        st.session_state.chat_history.append({"user": query.strip(), "bot": answer})
    for message in reversed(st.session_state.chat_history[-10:]):
        with st.chat_message("user"):
            st.write(message["user"])
        with st.chat_message("assistant"):
            st.write(message["bot"])
    if not st.session_state.chat_history:
        st.info("Assistant replies require GROQ_API_KEY and the optional LangChain Groq packages.")
