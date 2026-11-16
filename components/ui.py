import streamlit as st


def page_heading(kicker: str, title: str, subtitle: str = "") -> None:
    st.markdown(f'<div class="eyebrow">{kicker}</div><h1 style="margin:4px 0 2px">{title}</h1>', unsafe_allow_html=True)
    if subtitle:
        st.caption(subtitle)


def metric_card(label: str, value: str, unit: str = "") -> None:
    st.markdown(
        f'<div class="sensor-card"><div class="sensor-name">{label}</div>'
        f'<div class="sensor-value">{value}</div><div class="sensor-unit">{unit}</div></div>',
        unsafe_allow_html=True,
    )
