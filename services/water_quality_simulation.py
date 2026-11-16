"""Streamlit adapter preserving the separate Tkinter water-quality simulation logic.

All readings produced by this engine are simulated. The statistical baseline,
composite score, threshold percentile, grid, and movement heuristic mirror the
original Aquatic-Robotic-System/src/simulation.py implementation.
"""

from __future__ import annotations

import math
import random
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Robot:
    position: tuple[float, float]
    velocity: tuple[float, float] = (0.0, 0.0)
    heading: float = 0.0
    mode: str = "Patrolling"
    history: list[dict[str, Any]] = field(default_factory=list)


class WaterQualitySimulation:
    PH_LOW_THRESHOLD = 6.5
    PH_HIGH_THRESHOLD = 8.0
    TURBIDITY_THRESHOLD = 18.0
    SALINITY_THRESHOLD = 1.2
    ORIGIN_LATITUDE = 12.9716
    ORIGIN_LONGITUDE = 77.5946
    CELL_DEGREES = 0.0001
    BASELINE_SAMPLE_SIZE = 100
    ANOMALY_WEIGHTS = (1 / 3, 1 / 3, 1 / 3)
    MAX_MOVEMENT_SPEED = 1.5
    RANDOM_MOVEMENT_RANGE = 0.5

    def __init__(self, width: int = 12, height: int = 12, db_path: str | Path | None = None):
        self.width = width
        self.height = height
        self.db_path = Path(db_path) if db_path else None
        self.db = sqlite3.connect(str(self.db_path), check_same_thread=False) if self.db_path else None
        self._init_schema()
        self.run_id: str | None = None
        self.step_count = 0
        self.robot = Robot(position=(1.0, 1.0))
        self.grid = self._build_grid(width, height)
        self.baseline_stats: dict[str, dict[str, float]] | None = None
        self.anomaly_threshold: float | None = None

    def _init_schema(self) -> None:
        if self.db is None:
            return
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS baseline (
                id INTEGER PRIMARY KEY AUTOINCREMENT, ph REAL NOT NULL,
                turbidity REAL NOT NULL, salinity REAL NOT NULL,
                longitude REAL NOT NULL, latitude REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS timeseries_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT, recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
                step INTEGER NOT NULL, ph REAL NOT NULL, turbidity REAL NOT NULL,
                salinity REAL NOT NULL, longitude REAL NOT NULL, latitude REAL NOT NULL,
                anomaly_index REAL NOT NULL, anomaly_threshold REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS anomaly_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT, timeseries_id INTEGER NOT NULL,
                recorded_at TEXT NOT NULL DEFAULT (datetime('now')), latitude REAL,
                longitude REAL, anomaly_score REAL NOT NULL,
                FOREIGN KEY(timeseries_id) REFERENCES timeseries_data(id)
            );
            CREATE TABLE IF NOT EXISTS simulation_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        version = self.db.execute(
            "SELECT value FROM simulation_metadata WHERE key = 'composite_score_scale'"
        ).fetchone()
        if version is None:
            self.db.execute(
                """UPDATE timeseries_data
                   SET anomaly_index = anomaly_index / (1.0 + anomaly_index),
                       anomaly_threshold = anomaly_threshold / (1.0 + anomaly_threshold)
                   WHERE anomaly_index >= 0 AND anomaly_threshold >= 0"""
            )
            self.db.execute(
                """UPDATE anomaly_data
                   SET anomaly_score = anomaly_score / (1.0 + anomaly_score)
                   WHERE anomaly_score >= 0"""
            )
            self.db.execute(
                "INSERT INTO simulation_metadata(key, value) VALUES('composite_score_scale', 'bounded_v1')"
            )
        self.db.commit()

    def _build_grid(self, width: int, height: int) -> list[list[dict[str, float]]]:
        grid = []
        for y in range(height):
            row = []
            for x in range(width):
                ph, turbidity, salinity = 7.2, 12.0, 0.8
                if (x, y) == (5, 5):
                    ph -= 0.8
                    turbidity += 9.0
                elif (x, y) == (2, 7):
                    ph += 0.6
                    turbidity += 4.0
                row.append({"ph": ph + random.uniform(-0.05, 0.05), "turbidity": turbidity + random.uniform(-0.5, 0.5), "salinity": salinity + random.uniform(-0.02, 0.02)})
            grid.append(row)
        return grid

    @staticmethod
    def _stats(values: list[float]) -> dict[str, float]:
        ordered = sorted(values)
        n = len(ordered)
        mean = sum(ordered) / n if n else 0.0
        median = ordered[n // 2] if n % 2 else ((ordered[n // 2 - 1] + ordered[n // 2]) / 2 if n else 0.0)
        variance = sum((value - mean) ** 2 for value in ordered) / n if n else 0.0
        return {"mean": mean, "median": median, "std": math.sqrt(variance)}

    @staticmethod
    def _percentile(values: list[float], percentile: float) -> float:
        ordered = sorted(values)
        position = (len(ordered) - 1) * percentile / 100
        lower, upper = math.floor(position), math.ceil(position)
        if lower == upper:
            return ordered[lower]
        return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)

    def coordinate_for(self, x: int, y: int) -> tuple[float, float]:
        return self.ORIGIN_LATITUDE + y * self.CELL_DEGREES, self.ORIGIN_LONGITUDE + x * self.CELL_DEGREES

    def _grid_stats(self) -> dict[str, dict[str, float]]:
        return {key: self._stats([cell[key] for row in self.grid for cell in row]) for key in ("ph", "turbidity", "salinity")}

    def _recent_stats(self) -> dict[str, dict[str, float]]:
        history = self.robot.history[-20:]
        return {key: self._stats([item[key] for item in history]) for key in ("ph", "turbidity", "salinity")}

    def composite_anomaly_index(self, ph: float, turbidity: float, salinity: float) -> float:
        if self.baseline_stats is None:
            raise RuntimeError("Baseline not initialized")
        scores = [abs(value - self.baseline_stats[key]["mean"]) / max(self.baseline_stats[key]["std"], 1e-9) for key, value in (("ph", ph), ("turbidity", turbidity), ("salinity", salinity))]
        raw_score = sum(weight * score for weight, score in zip(self.ANOMALY_WEIGHTS, scores))
        # Monotonic compression keeps the weighted z-score anomaly metric in [0, 1).
        return raw_score / (1.0 + raw_score)

    def start_run(self, name: str = "streamlit-simulation") -> None:
        self.run_id = name
        self.step_count = 0
        self.robot = Robot(position=(1.0, 1.0))
        self._create_baseline()

    def _create_baseline(self) -> None:
        points = [(x, y) for y in range(self.height) for x in range(self.width)]
        selected = random.choices(points, k=self.BASELINE_SAMPLE_SIZE)
        rows = []
        for x, y in selected:
            cell = self.grid[y][x]
            lat, lon = self.coordinate_for(x, y)
            rows.append((cell["ph"], cell["turbidity"], cell["salinity"], lon, lat))
        if self.db is not None:
            self.db.executemany("INSERT INTO baseline(ph,turbidity,salinity,longitude,latitude) VALUES(?,?,?,?,?)", rows)
            self.db.commit()
        values = {key: [row[i] for row in rows] for i, key in enumerate(("ph", "turbidity", "salinity"))}
        self.baseline_stats = {key: self._stats(items) for key, items in values.items()}
        baseline_scores = [self.composite_anomaly_index(*sample) for sample in zip(values["ph"], values["turbidity"], values["salinity"])]
        self.anomaly_threshold = self._percentile(baseline_scores, 95)

    def read_cell(self, x: int, y: int) -> dict[str, float]:
        if not (0 <= x < self.width and 0 <= y < self.height):
            return {"ph": 7.2, "turbidity": 12.0, "salinity": 0.8}
        return self.grid[y][x]

    def sample_navigation_position(self, x: float, y: float, sample_step: int) -> dict[str, Any]:
        """Generate a fresh chemistry reading for a route location on the water grid.

        The base grid cell supplies spatial variation; independent measurement
        noise is added on every call so revisiting a location does not replay a
        frozen sensor value. All readings remain explicitly simulated.
        """
        if self.baseline_stats is None or self.anomaly_threshold is None:
            raise RuntimeError("Start a simulation run before sampling navigation positions")
        grid_x = max(0, min(self.width - 1, int(round(x))))
        grid_y = max(0, min(self.height - 1, int(round(y))))
        base = self.read_cell(grid_x, grid_y)
        ph = max(0.0, min(14.0, base["ph"] + random.uniform(-0.15, 0.15)))
        turbidity = max(0.0, base["turbidity"] + random.uniform(-1.5, 1.5))
        salinity = max(0.0, base["salinity"] + random.uniform(-0.05, 0.05))

        stats = self.baseline_stats
        z_score = (ph - stats["ph"]["mean"]) / max(0.1, stats["ph"]["std"])
        if abs(z_score) > 2.5 or turbidity > self.TURBIDITY_THRESHOLD:
            mode = "Investigating"
        elif abs(z_score) > 1.5:
            mode = "Anomaly"
        else:
            mode = "Patrolling"
        score = self.composite_anomaly_index(ph, turbidity, salinity)
        return {
            "step": int(sample_step),
            "x": float(x),
            "y": float(y),
            "grid_x": grid_x,
            "grid_y": grid_y,
            "ph": ph,
            "turbidity": turbidity,
            "salinity": salinity,
            "mode": mode,
            "z_score": z_score,
            "anomaly_index": score,
            "anomaly_threshold": self.anomaly_threshold,
            "water_quality_source": "simulation",
        }

    def _movement(self, ph: float, turbidity: float, salinity: float, stats: dict[str, dict[str, float]]) -> tuple[float, float]:
        dx = (stats["ph"]["mean"] - ph) * 0.7 + (stats["salinity"]["mean"] - salinity) * 0.22
        dy = (turbidity - stats["turbidity"]["mean"]) * 0.22 + (salinity - stats["salinity"]["mean"]) * 0.12
        speed = math.hypot(dx, dy)
        if speed > self.MAX_MOVEMENT_SPEED:
            scale = self.MAX_MOVEMENT_SPEED / speed
            dx *= scale
            dy *= scale
        return dx, dy

    def step(self) -> dict[str, Any]:
        if self.run_id is None:
            raise RuntimeError("Run not started")
        x, y = self.robot.position
        cell_x, cell_y = int(round(x)), int(round(y))
        cell = self.read_cell(cell_x, cell_y)
        ph, turbidity, salinity = cell["ph"], cell["turbidity"], cell["salinity"]
        stats = self._recent_stats() if self.robot.history else self._grid_stats()
        z_score = (ph - stats["ph"]["mean"]) / max(0.1, stats["ph"]["std"])
        if abs(z_score) > 2.5 or turbidity > self.TURBIDITY_THRESHOLD:
            self.robot.mode = "Investigating"
        elif abs(z_score) > 1.5:
            self.robot.mode = "Anomaly"
        else:
            self.robot.mode = "Patrolling"
        dx, dy = self._movement(ph, turbidity, salinity, stats)
        if abs(dx) < 0.15 and abs(dy) < 0.15:
            dx += random.uniform(-self.RANDOM_MOVEMENT_RANGE, self.RANDOM_MOVEMENT_RANGE)
            dy += random.uniform(-self.RANDOM_MOVEMENT_RANGE, self.RANDOM_MOVEMENT_RANGE)
        new_x, new_y = x + dx, y + dy
        if new_x <= 0.0 or new_x >= self.width - 1:
            dx, new_x = -dx, x - dx
        if new_y <= 0.0 or new_y >= self.height - 1:
            dy, new_y = -dy, y - dy
        new_x = max(0.0, min(self.width - 1, new_x))
        new_y = max(0.0, min(self.height - 1, new_y))
        self.robot.position = (new_x, new_y)
        self.robot.velocity = (dx, dy)
        self.robot.heading = math.degrees(math.atan2(dy, dx))
        anomaly_index = self.composite_anomaly_index(ph, turbidity, salinity)
        sample = {
            "step": self.step_count, "x": new_x, "y": new_y, "ph": ph,
            "turbidity": turbidity, "salinity": salinity, "mode": self.robot.mode,
            "z_score": z_score, "dx": dx, "dy": dy, "heading": self.robot.heading,
            "ph_mean": stats["ph"]["mean"], "ph_median": stats["ph"]["median"], "ph_std": stats["ph"]["std"],
            "turb_mean": stats["turbidity"]["mean"], "turb_median": stats["turbidity"]["median"],
            "sal_mean": stats["salinity"]["mean"], "sal_median": stats["salinity"]["median"],
            "anomaly_index": anomaly_index, "anomaly_threshold": self.anomaly_threshold,
        }
        self.robot.history.append(sample)
        lat, lon = self.coordinate_for(cell_x, cell_y)
        if self.db is not None:
            cur = self.db.execute("INSERT INTO timeseries_data(step,ph,turbidity,salinity,longitude,latitude,anomaly_index,anomaly_threshold) VALUES(?,?,?,?,?,?,?,?)", (self.step_count, ph, turbidity, salinity, lon, lat, anomaly_index, self.anomaly_threshold))
            if anomaly_index > self.anomaly_threshold:
                self.db.execute("INSERT INTO anomaly_data(timeseries_id,latitude,longitude,anomaly_score) VALUES(?,?,?,?)", (cur.lastrowid, lat, lon, anomaly_index))
            self.db.commit()
        self.step_count += 1
        return sample
