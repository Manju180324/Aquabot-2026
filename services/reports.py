from __future__ import annotations

from typing import Any

import pandas as pd


def make_detection_pdf(history: list[dict[str, Any]], counts: dict[str, int]) -> bytes | None:
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "AquaBot Detection Report", ln=True, align="C")
    pdf.set_font("Arial", size=11)
    pdf.cell(0, 9, "Detection totals: " + ", ".join(f"{name}: {count}" for name, count in counts.items()), ln=True)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 8, "Session history", ln=True)
    pdf.set_font("Arial", size=10)
    for item in history:
        text = f"{item.get('Time', '')} | {item.get('Waste', '')} | confidence {item.get('Confidence', '')}"
        pdf.multi_cell(0, 7, text.encode("latin-1", "replace").decode("latin-1"))
    output = pdf.output(dest="S")
    return output.encode("latin-1") if isinstance(output, str) else bytes(output)


def make_navigation_pdf(mission: dict[str, Any], movements: pd.DataFrame) -> bytes | None:
    try:
        from fpdf import FPDF
    except ImportError:
        return None
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "AquaBot Navigation Mission Log", ln=True, align="C")
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(0, 7, f"Mission ID: {mission.get('mission_id', '')}\nStatus: {mission.get('status', '')}\nStarted: {mission.get('started_at', '')}\nRecorded route points: {len(movements)}")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 9)
    pdf.multi_cell(0, 6, "GPS latitude/longitude are from recorded telemetry. pH, turbidity, salinity, and anomaly scores are simulated readings aligned with each playback route point.")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 8)
    pdf.cell(13, 7, "Point", border=1)
    pdf.cell(36, 7, "Recorded at", border=1)
    pdf.cell(33, 7, "GPS lat, lon", border=1)
    pdf.cell(23, 7, "pH sim", border=1)
    pdf.cell(27, 7, "Turbidity sim", border=1)
    pdf.cell(24, 7, "Salinity sim", border=1, ln=True)
    pdf.set_font("Arial", size=7)
    for row in movements.itertuples(index=False):
        if pdf.get_y() > 270:
            pdf.add_page()
        pdf.cell(13, 6, str(row.route_index), border=1)
        pdf.cell(36, 6, str(row.recorded_at)[:19], border=1)
        pdf.cell(33, 6, f"{row.gps_lat:.6f}, {row.gps_lon:.6f}", border=1)
        pdf.cell(23, 6, f"{row.ph:.3f}", border=1)
        pdf.cell(27, 6, f"{row.turbidity:.3f}", border=1)
        pdf.cell(24, 6, f"{row.salinity:.3f}", border=1, ln=True)
    output = pdf.output(dest="S")
    return output.encode("latin-1") if isinstance(output, str) else bytes(output)
