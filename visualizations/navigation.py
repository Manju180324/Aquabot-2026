from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go


OCEAN = "#071c2b"
CYAN = "#59e1e8"
BLUE = "#4e91ff"


def navigation_figure(frame: pd.DataFrame, cursor: int | None = None) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor=OCEAN,
        margin=dict(l=12, r=12, t=18, b=12), height=440,
        xaxis_title="Longitude", yaxis_title="Latitude", showlegend=True,
        legend=dict(orientation="h", y=1.08, x=0),
        xaxis=dict(showgrid=True, gridcolor="rgba(135,190,210,.12)", zeroline=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(135,190,210,.12)", zeroline=False, scaleanchor="x", scaleratio=1),
        hovermode="closest",
    )
    if frame.empty or not {"gps_lat", "gps_lon"}.issubset(frame.columns):
        fig.add_annotation(text="GPS coordinates are not available in the loaded telemetry.", showarrow=False, font=dict(color="#9bb9c8"))
        return fig

    idx = len(frame) - 1 if cursor is None else max(0, min(int(cursor), len(frame) - 1))
    done = frame.iloc[:idx + 1]
    upcoming = frame.iloc[idx:]
    fig.add_trace(go.Scatter(x=done["gps_lon"], y=done["gps_lat"], mode="lines", name="Completed trail", line=dict(color=CYAN, width=3), hovertemplate="Lon %{x:.6f}<br>Lat %{y:.6f}<extra>Completed</extra>"))
    if len(upcoming) > 1:
        fig.add_trace(go.Scatter(x=upcoming["gps_lon"], y=upcoming["gps_lat"], mode="lines", name="Upcoming route", line=dict(color=BLUE, width=2, dash="dash"), hovertemplate="Lon %{x:.6f}<br>Lat %{y:.6f}<extra>Upcoming</extra>"))
    waypoint_step = max(1, len(frame) // 8)
    waypoints = frame.iloc[::waypoint_step]
    fig.add_trace(go.Scatter(x=waypoints["gps_lon"], y=waypoints["gps_lat"], mode="markers", name="Route points", marker=dict(color="#c7f8ff", size=7, symbol="circle-open", line=dict(width=1)), customdata=waypoints["timestamp"].astype(str), hovertemplate="Waypoint<br>%{customdata}<extra></extra>"))
    row = frame.iloc[idx]
    heading = 0.0
    if idx < len(frame) - 1:
        next_row = frame.iloc[idx + 1]
        delta_lat = float(next_row["gps_lat"] - row["gps_lat"])
        delta_lon = float(next_row["gps_lon"] - row["gps_lon"])
        heading = math.degrees(math.atan2(delta_lon, delta_lat))
    fig.add_trace(go.Scatter(x=[row["gps_lon"]], y=[row["gps_lat"]], mode="markers", name="AquaBot", marker=dict(color="#8af7e0", size=18, symbol="triangle-up", angle=heading, line=dict(color="#061522", width=2)), customdata=[[str(row["timestamp"]), row.get("speed", None)]], hovertemplate="Current position<br>%{customdata[0]}<br>Speed: %{customdata[1]}<extra></extra>"))
    fig.add_trace(go.Scatter(x=[frame["gps_lon"].iloc[0]], y=[frame["gps_lat"].iloc[0]], mode="markers+text", name="Start", text=["START"], textposition="top center", marker=dict(color="#5bc8ff", size=10, symbol="diamond"), hovertemplate="Mission start<extra></extra>"))
    fig.add_trace(go.Scatter(x=[frame["gps_lon"].iloc[-1]], y=[frame["gps_lat"].iloc[-1]], mode="markers+text", name="Destination", text=["DEST"], textposition="top center", marker=dict(color="#ffbd6d", size=10, symbol="square"), hovertemplate="Recorded route end<extra></extra>"))
    return fig
