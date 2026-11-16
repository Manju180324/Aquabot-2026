from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go


def simulation_figure(grid: list[list[dict[str, float]]], history: list[dict], position: tuple[float, float], heading: float) -> go.Figure:
    height, width = len(grid), len(grid[0])
    values = [[cell["turbidity"] for cell in row] for row in grid]
    fig = go.Figure(go.Heatmap(z=values, x=list(range(width)), y=list(range(height)), colorscale=[[0, "#0c4967"], [0.55, "#168ba4"], [1, "#8cddcf"]], colorbar=dict(title="Turbidity<br>sim units"), hovertemplate="Grid cell (%{x}, %{y})<br>Simulated turbidity: %{z:.2f}<extra></extra>"))
    if history:
        path = pd.DataFrame(history)
        fig.add_trace(go.Scatter(x=path["x"], y=path["y"], mode="lines+markers", name="Simulated trail", line=dict(color="#ffbb72", width=2), marker=dict(size=4, color="#ffe4a8"), hovertemplate="Step %{customdata}<extra>Trail</extra>", customdata=path["step"]))
    fig.add_trace(go.Scatter(x=[position[0]], y=[position[1]], mode="markers", name="AquaBot (simulation)", marker=dict(color="#69ffe4", size=17, symbol="triangle-up", angle=heading, line=dict(color="#032235", width=2)), hovertemplate="Simulated robot position<extra></extra>"))
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#071c2b", margin=dict(l=5, r=10, t=12, b=5), height=440, xaxis_title="Grid X", yaxis_title="Grid Y", yaxis=dict(autorange="reversed", dtick=1), xaxis=dict(dtick=1), legend=dict(orientation="h", y=1.08))
    return fig


def history_figure(history: list[dict]) -> go.Figure:
    frame = pd.DataFrame(history)
    fig = go.Figure()
    if not frame.empty:
        fig.add_trace(go.Scatter(x=frame["step"], y=frame["ph"], name="pH", line=dict(color="#58dfe5")))
        fig.add_trace(go.Scatter(x=frame["step"], y=frame["turbidity"], name="Turbidity", yaxis="y2", line=dict(color="#ffbd6d")))
        fig.add_trace(go.Scatter(x=frame["step"], y=frame["salinity"], name="Salinity", yaxis="y3", line=dict(color="#9a9cff")))
    fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="#071c2b", margin=dict(l=8, r=55, t=16, b=8), height=270, xaxis_title="Simulation step", yaxis=dict(title="pH"), yaxis2=dict(title="Turbidity (sim units)", overlaying="y", side="right"), hovermode="x unified", legend=dict(orientation="h", y=1.12))
    return fig
