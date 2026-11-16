from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from services.telemetry import FIELD_LABELS


CHART_TEMPLATE = "plotly_dark"


def sensor_trend(frame: pd.DataFrame, field: str, title: str | None = None) -> go.Figure:
    label = FIELD_LABELS.get(field, (field.replace("_", " ").title(), "CSV units not specified"))[0]
    fig = px.line(frame, x="timestamp", y=field, title=title or label, template=CHART_TEMPLATE, markers=False)
    fig.update_traces(line=dict(color="#59e1e8", width=2), hovertemplate="%{x}<br>%{y:.4f}<extra>" + label + "</extra>")
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#071c2b", margin=dict(l=8, r=12, t=42, b=8), height=260, xaxis_title=None, yaxis_title=FIELD_LABELS.get(field, (field, ""))[1], hovermode="x unified")
    return fig


def waste_counts_figure(counts: dict[str, int]) -> go.Figure:
    frame = pd.DataFrame({"Waste class": list(counts), "Detections": list(counts.values())})
    fig = px.bar(frame, x="Waste class", y="Detections", color="Waste class", template=CHART_TEMPLATE, color_discrete_sequence=["#58dfe5", "#5897ff", "#ffbd6d"])
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#071c2b", margin=dict(l=8, r=8, t=12, b=8), height=300, showlegend=False)
    return fig
