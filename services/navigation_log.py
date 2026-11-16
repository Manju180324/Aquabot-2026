from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd


class NavigationMissionStore:
    """Persistent per-route-point log; GPS is recorded telemetry, chemistry is simulated."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS navigation_missions (
                mission_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL DEFAULT (datetime('now')),
                ended_at TEXT,
                source_name TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Running'
            );
            CREATE TABLE IF NOT EXISTS navigation_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                mission_id TEXT NOT NULL,
                route_index INTEGER NOT NULL,
                recorded_at TEXT,
                logged_at TEXT NOT NULL DEFAULT (datetime('now')),
                gps_lat REAL NOT NULL,
                gps_lon REAL NOT NULL,
                x REAL,
                y REAL,
                water_grid_x REAL,
                water_grid_y REAL,
                speed REAL,
                ph REAL NOT NULL,
                turbidity REAL NOT NULL,
                salinity REAL NOT NULL,
                water_quality_source TEXT NOT NULL DEFAULT 'simulation',
                anomaly_index REAL,
                anomaly_threshold REAL,
                score_scale_version INTEGER NOT NULL DEFAULT 2,
                UNIQUE(mission_id, route_index),
                FOREIGN KEY(mission_id) REFERENCES navigation_missions(mission_id)
            );
            CREATE INDEX IF NOT EXISTS idx_navigation_movements_mission_route
                ON navigation_movements(mission_id, route_index);
        """)
        existing_columns = {row[1] for row in self.connection.execute("PRAGMA table_info(navigation_movements)")}
        for column in ("water_grid_x", "water_grid_y"):
            if column not in existing_columns:
                self.connection.execute(f"ALTER TABLE navigation_movements ADD COLUMN {column} REAL")
        if "score_scale_version" not in existing_columns:
            self.connection.execute(
                "ALTER TABLE navigation_movements ADD COLUMN score_scale_version INTEGER NOT NULL DEFAULT 1"
            )
        self.connection.execute(
            """UPDATE navigation_movements
               SET anomaly_index = CASE WHEN anomaly_index > 1.0
                                        THEN anomaly_index / (1.0 + anomaly_index)
                                        ELSE anomaly_index END,
                   anomaly_threshold = CASE WHEN anomaly_threshold > 1.0
                                            THEN anomaly_threshold / (1.0 + anomaly_threshold)
                                            ELSE anomaly_threshold END,
                   score_scale_version = 2
               WHERE score_scale_version = 1
                  OR anomaly_index > 1.0
                  OR anomaly_threshold > 1.0"""
        )
        self.connection.execute(
            "UPDATE navigation_movements SET score_scale_version = 2 WHERE score_scale_version = 1"
        )
        self.connection.commit()

    def create_mission(self, mission_id: str, source_name: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO navigation_missions(mission_id, source_name) VALUES(?, ?)",
            (mission_id, source_name),
        )
        self.connection.commit()

    def finish_mission(self, mission_id: str, status: str) -> None:
        self.connection.execute(
            "UPDATE navigation_missions SET status = ?, ended_at = datetime('now') WHERE mission_id = ?",
            (status, mission_id),
        )
        self.connection.commit()

    def add_movement(self, mission_id: str, route_index: int, route_row: pd.Series, sample: dict[str, Any]) -> bool:
        cursor = self.connection.execute(
            """INSERT OR IGNORE INTO navigation_movements(
                mission_id, route_index, recorded_at, gps_lat, gps_lon, x, y,
                water_grid_x, water_grid_y, speed,
                ph, turbidity, salinity, water_quality_source, anomaly_index,
                anomaly_threshold, score_scale_version
            ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'simulation', ?, ?, 2)""",
            (
                mission_id,
                route_index,
                str(route_row.get("timestamp", "")),
                float(route_row["gps_lat"]),
                float(route_row["gps_lon"]),
                _optional_float(route_row.get("x")),
                _optional_float(route_row.get("y")),
                _optional_float(sample.get("grid_x")),
                _optional_float(sample.get("grid_y")),
                _optional_float(route_row.get("speed")),
                float(sample["ph"]),
                float(sample["turbidity"]),
                float(sample["salinity"]),
                float(sample["anomaly_index"]),
                float(sample["anomaly_threshold"]),
            ),
        )
        self.connection.commit()
        return cursor.rowcount > 0

    def missions(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """SELECT m.mission_id AS mission_id, m.started_at, m.ended_at, m.status,
                      m.source_name, COUNT(v.id) AS movement_count,
                      MIN(v.recorded_at) AS first_recorded_at,
                      MAX(v.recorded_at) AS last_recorded_at
               FROM navigation_missions m
               LEFT JOIN navigation_movements v ON v.mission_id = m.mission_id
               GROUP BY m.mission_id
               ORDER BY m.started_at DESC""",
            self.connection,
        )

    def movements(self, mission_id: str) -> pd.DataFrame:
        return pd.read_sql_query(
            """SELECT route_index, recorded_at, logged_at, gps_lat, gps_lon, x, y,
                      water_grid_x, water_grid_y, speed,
                      ph, turbidity, salinity, water_quality_source, anomaly_index, anomaly_threshold
               FROM navigation_movements
               WHERE mission_id = ?
               ORDER BY route_index""",
            self.connection,
            params=(mission_id,),
        )

    def close(self) -> None:
        self.connection.close()


def _optional_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def record_route_range(
    store: NavigationMissionStore,
    mission_id: str,
    frame: pd.DataFrame,
    first_index: int,
    last_index: int,
    water_engine: Any,
) -> int:
    """Record each route point with GPS and a fresh, location-based simulated reading."""
    recorded = 0
    upper_bound = min(int(last_index), len(frame) - 1)
    lon_min, lon_max = float(frame["gps_lon"].min()), float(frame["gps_lon"].max())
    lat_min, lat_max = float(frame["gps_lat"].min()), float(frame["gps_lat"].max())
    lon_span, lat_span = max(lon_max - lon_min, 1e-12), max(lat_max - lat_min, 1e-12)
    for route_index in range(max(0, int(first_index)), upper_bound + 1):
        route_row = frame.iloc[route_index]
        grid_x = (float(route_row["gps_lon"]) - lon_min) / lon_span * (water_engine.width - 1)
        grid_y = (float(route_row["gps_lat"]) - lat_min) / lat_span * (water_engine.height - 1)
        sample = water_engine.sample_navigation_position(grid_x, grid_y, route_index)
        if store.add_movement(mission_id, route_index, route_row, sample):
            recorded += 1
    return recorded
