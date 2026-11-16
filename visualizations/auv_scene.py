from __future__ import annotations

import math

import pandas as pd


def _xy(frame: pd.DataFrame, lat: float, lon: float) -> tuple[float, float]:
    min_lon, max_lon = float(frame["gps_lon"].min()), float(frame["gps_lon"].max())
    min_lat, max_lat = float(frame["gps_lat"].min()), float(frame["gps_lat"].max())
    x_span, y_span = max(max_lon - min_lon, 1e-9), max(max_lat - min_lat, 1e-9)
    x = 70 + (lon - min_lon) / x_span * 860
    y = 250 - (lat - min_lat) / y_span * 185
    return x, y


def scene_html(frame: pd.DataFrame, cursor: int) -> str:
    if frame.empty or not {"gps_lat", "gps_lon"}.issubset(frame.columns):
        return '<div class="panel" style="height:310px;display:grid;place-items:center;color:#9bb9c8">No GPS route available</div>'
    idx = max(0, min(cursor, len(frame) - 1))
    point_step = max(1, len(frame) // 110)
    route = frame.iloc[::point_step]
    if route.index[-1] != frame.index[-1]:
        route = pd.concat([route, frame.iloc[[-1]]])
    done = route.loc[route.index <= frame.index[idx]]
    future = route.loc[route.index >= frame.index[idx]]

    def points(rows: pd.DataFrame) -> str:
        return " ".join(f"{_xy(frame, float(row.gps_lat), float(row.gps_lon))[0]:.1f},{_xy(frame, float(row.gps_lat), float(row.gps_lon))[1]:.1f}" for row in rows.itertuples())

    current = frame.iloc[idx]
    x, y = _xy(frame, float(current["gps_lat"]), float(current["gps_lon"]))
    if idx < len(frame) - 1:
        nxt = frame.iloc[idx + 1]
        nx, ny = _xy(frame, float(nxt["gps_lat"]), float(nxt["gps_lon"]))
        heading = math.degrees(math.atan2(ny - y, nx - x)) + 90
    else:
        heading = 0
    waypoints = frame.iloc[::max(1, len(frame) // 7)]
    markers = "".join(f'<circle cx="{_xy(frame, float(row.gps_lat), float(row.gps_lon))[0]:.1f}" cy="{_xy(frame, float(row.gps_lat), float(row.gps_lon))[1]:.1f}" r="4" fill="#d5fbff" stroke="#153d55" stroke-width="2"/>' for row in waypoints.itertuples())
    progress = (idx + 1) / len(frame) * 100
    return f'''
    <div style="border:1px solid rgba(89,225,232,.2);border-radius:18px;overflow:hidden;background:#061b2b;box-shadow:0 16px 42px rgba(0,0,0,.2)">
      <div style="display:flex;justify-content:space-between;padding:15px 18px 4px;position:relative;z-index:2"><span style="font:500 11px 'DM Mono',monospace;letter-spacing:.14em;color:#59e1e8">AUV · RECORDED ROUTE PLAYBACK</span><span style="font:11px 'DM Mono',monospace;color:#9bb9c8">{progress:.1f}% · POINT {idx + 1:,}/{len(frame):,}</span></div>
      <svg viewBox="0 0 1000 310" role="img" aria-label="AquaBot route animation" style="display:block;width:100%;height:auto;min-height:220px">
        <defs>
          <linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a3048"/><stop offset="1" stop-color="#031320"/></linearGradient>
          <radialGradient id="glow"><stop offset="0" stop-color="#42e1e4" stop-opacity=".19"/><stop offset="1" stop-color="#42e1e4" stop-opacity="0"/></radialGradient>
          <linearGradient id="hull" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d7fbff"/><stop offset=".48" stop-color="#54dfe5"/><stop offset="1" stop-color="#167caa"/></linearGradient>
          <filter id="soft"><feGaussianBlur stdDeviation="8"/></filter>
        </defs>
        <rect width="1000" height="310" fill="url(#sea)"/><ellipse cx="{x:.1f}" cy="{y:.1f}" rx="190" ry="150" fill="url(#glow)"/>
        <path d="M0 235 Q120 215 240 235 T480 235 T720 235 T1000 235 V310 H0Z" fill="#0a3345" opacity=".38"/>
        <path d="M0 272 Q150 250 300 272 T600 272 T900 272 T1200 272" fill="none" stroke="#48c9d6" stroke-opacity=".12" stroke-width="2"/>
        <polyline points="{points(future)}" fill="none" stroke="#4e91ff" stroke-width="3" stroke-dasharray="8 9" stroke-linecap="round" opacity=".65"/>
        <polyline points="{points(done)}" fill="none" stroke="#59e1e8" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
        {markers}
        <circle cx="{_xy(frame, float(frame.iloc[-1].gps_lat), float(frame.iloc[-1].gps_lon))[0]:.1f}" cy="{_xy(frame, float(frame.iloc[-1].gps_lat), float(frame.iloc[-1].gps_lon))[1]:.1f}" r="8" fill="#ffbd6d" stroke="#071c2b" stroke-width="3"/>
        <g transform="translate({x:.1f} {y:.1f}) rotate({heading:.1f})">
          <circle r="24" fill="#59e1e8" opacity=".2" filter="url(#soft)"/>
          <g class="auv-bob">
            <path d="M-24 0 L-17 -12 L13 -12 L26 0 L18 9 L-16 9Z" fill="url(#hull)" stroke="#c2ffff" stroke-width="1.5"/>
            <path d="M-7 -12 L-3 -21 L8 -21 L13 -12Z" fill="#a8f7ed" stroke="#e7ffff" stroke-width="1"/>
            <path d="M-18 4 L17 4" stroke="#0b5574" stroke-width="2"/>
            <circle cx="2" cy="-17" r="2" fill="#061522"/>
            <path d="M0 13 L0 21" stroke="#59e1e8" stroke-width="2" stroke-linecap="round"/>
          </g>
        </g>
        <circle class="scene-bubble bubble-a" cx="130" cy="275" r="4"/><circle class="scene-bubble bubble-b" cx="825" cy="250" r="6"/><circle class="scene-bubble bubble-c" cx="690" cy="290" r="3"/>
        <text x="24" y="32" fill="#9bb9c8" font-family="monospace" font-size="11">COMPLETED TRACK</text><line x1="155" y1="28" x2="196" y2="28" stroke="#59e1e8" stroke-width="3"/>
        <text x="215" y="32" fill="#9bb9c8" font-family="monospace" font-size="11">UPCOMING</text><line x1="300" y1="28" x2="341" y2="28" stroke="#4e91ff" stroke-width="3" stroke-dasharray="6 5"/>
      </svg>
      <style>@keyframes aquabob{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-5px)}}}}@keyframes aquarise{{0%{{transform:translateY(15px);opacity:0}}20%{{opacity:.6}}100%{{transform:translateY(-100px);opacity:0}}}}.auv-bob{{animation:aquabob 2.4s ease-in-out infinite;transform-box:fill-box;transform-origin:center}}.scene-bubble{{fill:none;stroke:#9bf6f1;stroke-opacity:.55;animation:aquarise 5s linear infinite}}.bubble-b{{animation-delay:1.6s;animation-duration:6s}}.bubble-c{{animation-delay:3s;animation-duration:4.7s}}</style>
      <div style="height:3px;background:#102e41"><div style="height:3px;width:{progress:.2f}%;background:linear-gradient(90deg,#4e91ff,#59e1e8);box-shadow:0 0 14px #59e1e8;transition:width .4s ease"></div></div>
    </div>'''
