from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def anomaly_locations_figure(movements: pd.DataFrame, anomalies: pd.DataFrame, threshold: float) -> go.Figure:
    fig = go.Figure()
    if not movements.empty:
        fig.add_trace(go.Scatter(
            x=movements["gps_lon"], y=movements["gps_lat"],
            mode="lines", name="Recorded route",
            line=dict(color="rgba(89,225,232,.4)", width=2),
            hoverinfo="skip",
        ))
    if not anomalies.empty:
        custom = anomalies[["route_index", "recorded_at", "water_grid_x", "water_grid_y", "ph", "turbidity", "salinity", "anomaly_score"]].to_numpy()
        fig.add_trace(go.Scatter(
            x=anomalies["gps_lon"], y=anomalies["gps_lat"],
            mode="markers", name=f"Score > {threshold:.2f}",
            marker=dict(size=11, color=anomalies["anomaly_score"], colorscale="Turbo", showscale=True, colorbar=dict(title="Score"), line=dict(color="#fff1dc", width=1)),
            customdata=custom,
            hovertemplate=(
                "Route point %{customdata[0]}<br>Recorded: %{customdata[1]}"
                "<br>GPS: %{y:.6f}, %{x:.6f}"
                "<br>Water grid: (%{customdata[2]:.2f}, %{customdata[3]:.2f})"
                "<br>pH (sim): %{customdata[4]:.3f}"
                "<br>Turbidity (sim): %{customdata[5]:.3f}"
                "<br>Salinity (sim): %{customdata[6]:.3f}"
                "<br>Composite score: %{customdata[7]:.3f}<extra></extra>"
            ),
        ))
    if movements.empty:
        fig.add_annotation(text="No navigation movement records are saved yet.", showarrow=False, font=dict(color="#9bb9c8"))
    elif anomalies.empty:
        fig.add_annotation(text=f"No logged simulated-water-quality score exceeds {threshold:.2f}.", showarrow=False, font=dict(color="#9bb9c8"))
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#071c2b",
        margin=dict(l=12, r=12, t=18, b=12), height=420,
        xaxis_title="Longitude", yaxis_title="Latitude", hovermode="closest",
        xaxis=dict(showgrid=True, gridcolor="rgba(135,190,210,.12)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(135,190,210,.12)", scaleanchor="x", scaleratio=1),
        legend=dict(orientation="h", y=1.08, x=0),
    )
    return fig
