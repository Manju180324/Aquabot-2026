from __future__ import annotations

import pandas as pd


ANOMALY_THRESHOLD = 0.70
ANOMALY_WEIGHTS = (1 / 3, 1 / 3, 1 / 3)
ANOMALY_BIAS = 0.0


def threshold_anomalies(movements: pd.DataFrame, threshold: float = ANOMALY_THRESHOLD) -> pd.DataFrame:
    """Select logged simulated-chemistry route points whose composite score exceeds threshold."""
    if movements.empty or "anomaly_index" not in movements.columns:
        return movements.iloc[0:0].copy()
    scores = pd.to_numeric(movements["anomaly_index"], errors="coerce")
    is_simulated = movements.get("water_quality_source", pd.Series("simulation", index=movements.index)).eq("simulation")
    result = movements.loc[is_simulated & scores.gt(threshold)].copy()
    result["anomaly_score"] = pd.to_numeric(result["anomaly_index"], errors="coerce")
    return result.sort_values("anomaly_score", ascending=False).reset_index(drop=True)
