from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from config.settings import DEFAULT_TELEMETRY_PATH
from services.processing import pipeline_stages
from services.navigation_log import NavigationMissionStore, record_route_range
from services.anomaly_detection import ANOMALY_THRESHOLD, threshold_anomalies
from services.assistant import summarize_dashboard_data
from services.telemetry import load_telemetry, prepare_telemetry
from services.water_quality_simulation import WaterQualitySimulation
from visualizations.auv_scene import scene_html
from visualizations.navigation import navigation_figure


class AssistantContextTests(unittest.TestCase):
    def test_dashboard_summary_excludes_gps_coordinates(self):
        frame = pd.DataFrame({
            "gps_lat": [12.345678],
            "gps_lon": [77.123456],
            "speed": [1.5],
            "timestamp": ["2025-01-01T00:00:00Z"],
        })

        summary = summarize_dashboard_data(
            frame=frame,
            received_rows=1,
            waste_counts={"Plastic": 2},
            mission_status="Running",
            mission_cursor=0,
            water_quality_values={"ph": 7.2, "turbidity": 12.0, "salinity": 0.8},
        )

        self.assertIn('"valid_route_rows": 1', summary)
        self.assertIn('"average": 1.5', summary)
        self.assertNotIn("12.345678", summary)
        self.assertNotIn("77.123456", summary)


class TelemetryServiceTests(unittest.TestCase):
    def test_existing_csv_is_loaded_and_fields_are_preserved(self):
        raw, source = load_telemetry(path=DEFAULT_TELEMETRY_PATH)
        result = prepare_telemetry(raw)
        self.assertEqual(source, DEFAULT_TELEMETRY_PATH.name)
        self.assertGreater(result["received"], 0)
        self.assertEqual(result["processed"], result["received"])
        self.assertTrue({"timestamp", "gps_lat", "gps_lon", "speed", "ultrasonic", "lora_rssi", "lora_snr"}.issubset(result["data"].columns))
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(result["data"]["timestamp"]))

    def test_invalid_route_rows_are_counted(self):
        raw = pd.DataFrame({
            "timestamp": ["2025-01-01T00:00:00Z", "not-a-date"],
            "gps_lat": [12.0, 12.1],
            "gps_lon": [77.0, None],
            "speed": [1.0, 2.0],
        })
        result = prepare_telemetry(raw)
        self.assertEqual(result["received"], 2)
        self.assertEqual(result["processed"], 1)
        self.assertEqual(result["rejected"], 1)

    def test_pipeline_counts_use_measured_source_rows(self):
        result = prepare_telemetry(pd.DataFrame({
            "timestamp": ["2025-01-01T00:00:00Z", "bad"],
            "gps_lat": [12.0, None], "gps_lon": [77.0, 77.1],
        }))
        stages = pipeline_stages(result)
        cleaning = next(stage for stage in stages if stage["stage"] == "Data cleaning")
        anomaly = next(stage for stage in stages if stage["stage"] == "Analysis / anomaly detection")
        self.assertEqual((cleaning["received"], cleaning["processed"], cleaning["rejected"]), (2, 1, 1))
        self.assertEqual(anomaly["state"], "not configured")

    def test_route_visualizations_use_loaded_gps_rows(self):
        result = prepare_telemetry(pd.read_csv(DEFAULT_TELEMETRY_PATH))
        self.assertGreater(len(navigation_figure(result["data"], 1).data), 0)
        self.assertIn("RECORDED ROUTE PLAYBACK", scene_html(result["data"], 1))


class WaterQualitySimulationTests(unittest.TestCase):
    def test_original_simulation_logic_and_sqlite_persistence(self):
        engine = WaterQualitySimulation(db_path=":memory:")
        engine.start_run("test-run")
        sample = engine.step()
        self.assertIn(sample["mode"], {"Patrolling", "Anomaly", "Investigating"})
        self.assertGreaterEqual(sample["anomaly_threshold"], 0)
        self.assertLess(sample["anomaly_threshold"], 1)
        self.assertGreaterEqual(sample["anomaly_index"], 0)
        self.assertLess(sample["anomaly_index"], 1)
        self.assertEqual(len(engine.robot.history), 1)
        counts = {table: engine.db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in ("baseline", "timeseries_data")}
        self.assertEqual(counts["baseline"], engine.BASELINE_SAMPLE_SIZE)
        self.assertEqual(counts["timeseries_data"], 1)
        engine.db.close()

    def test_composite_score_is_monotonic_and_bounded(self):
        engine = WaterQualitySimulation()
        engine.baseline_stats = {
            "ph": {"mean": 0.0, "std": 1.0},
            "turbidity": {"mean": 0.0, "std": 1.0},
            "salinity": {"mean": 0.0, "std": 1.0},
        }
        scores = [engine.composite_anomaly_index(value, value, value) for value in (0.0, 1.0, 3.0, 100.0)]
        self.assertEqual(scores[0], 0.0)
        self.assertEqual(scores[2], 0.75)  # R=3 -> R/(1+R)=0.75
        self.assertEqual(scores, sorted(scores))
        self.assertTrue(all(0 <= score < 1 for score in scores))

    def test_navigation_grid_resamples_chemistry_on_each_visit(self):
        engine = WaterQualitySimulation()
        engine.start_run("dynamic-grid-test")
        first = engine.sample_navigation_position(5.0, 5.0, 0)
        revisit = engine.sample_navigation_position(5.0, 5.0, 1)
        self.assertEqual((first["grid_x"], first["grid_y"]), (5, 5))
        self.assertEqual(first["water_quality_source"], "simulation")
        self.assertNotEqual(
            (first["ph"], first["turbidity"], first["salinity"]),
            (revisit["ph"], revisit["turbidity"], revisit["salinity"]),
        )


class NavigationMissionLogTests(unittest.TestCase):
    def test_legacy_navigation_scores_are_migrated_to_bounded_scale(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "legacy.db"
            connection = sqlite3.connect(db_path)
            connection.executescript("""
                CREATE TABLE navigation_missions (
                    mission_id TEXT PRIMARY KEY, started_at TEXT NOT NULL DEFAULT (datetime('now')),
                    ended_at TEXT, source_name TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Running'
                );
                CREATE TABLE navigation_movements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, mission_id TEXT NOT NULL,
                    route_index INTEGER NOT NULL, recorded_at TEXT,
                    logged_at TEXT NOT NULL DEFAULT (datetime('now')),
                    gps_lat REAL NOT NULL, gps_lon REAL NOT NULL, x REAL, y REAL, speed REAL,
                    ph REAL NOT NULL, turbidity REAL NOT NULL, salinity REAL NOT NULL,
                    water_quality_source TEXT NOT NULL DEFAULT 'simulation',
                    anomaly_index REAL, anomaly_threshold REAL,
                    UNIQUE(mission_id, route_index)
                );
                INSERT INTO navigation_missions(mission_id, source_name) VALUES('legacy', 'old.csv');
                INSERT INTO navigation_movements(
                    mission_id, route_index, gps_lat, gps_lon, ph, turbidity, salinity,
                    anomaly_index, anomaly_threshold
                ) VALUES('legacy', 0, 12.0, 77.0, 7.0, 12.0, 0.8, 3.0, 1.5);
            """)
            connection.commit()
            connection.close()

            store = NavigationMissionStore(db_path)
            row = store.movements("legacy").iloc[0]
            self.assertEqual(row["anomaly_index"], 0.75)
            self.assertEqual(row["anomaly_threshold"], 0.6)
            store.close()

    def test_every_played_route_row_is_persisted_with_gps_and_simulated_chemistry(self):
        frame = pd.DataFrame({
            "timestamp": pd.date_range("2025-01-01", periods=4, freq="200ms", tz="UTC"),
            "gps_lat": [12.1, 12.2, 12.3, 12.4],
            "gps_lon": [77.1, 77.2, 77.3, 77.4],
            "speed": [0.8, 0.9, 1.0, 1.1],
        })
        with tempfile.TemporaryDirectory() as temp_dir:
            store = NavigationMissionStore(Path(temp_dir) / "mission.db")
            store.create_mission("test-mission", "test.csv")
            engine = WaterQualitySimulation()
            engine.start_run("test-navigation-water-quality")

            recorded = record_route_range(store, "test-mission", frame, 0, 3, engine)
            movements = store.movements("test-mission")
            self.assertEqual(recorded, 4)
            self.assertEqual(len(movements), len(frame))
            self.assertEqual(movements["route_index"].tolist(), [0, 1, 2, 3])
            self.assertEqual(movements["gps_lat"].tolist(), frame["gps_lat"].tolist())
            self.assertEqual(movements["gps_lon"].tolist(), frame["gps_lon"].tolist())
            self.assertTrue({"ph", "turbidity", "salinity"}.issubset(movements.columns))
            self.assertTrue({"water_grid_x", "water_grid_y"}.issubset(movements.columns))
            self.assertGreater(movements["ph"].nunique(), 1)
            self.assertGreater(movements["turbidity"].nunique(), 1)
            self.assertGreater(movements["salinity"].nunique(), 1)
            self.assertEqual(set(movements["water_quality_source"]), {"simulation"})

            # Replaying the same indices cannot create duplicate persistent rows.
            record_route_range(store, "test-mission", frame, 0, 3, engine)
            self.assertEqual(len(store.movements("test-mission")), 4)
            store.close()

            reopened = NavigationMissionStore(Path(temp_dir) / "mission.db")
            persisted = reopened.movements("test-mission")
            self.assertEqual(len(persisted), 4)
            self.assertEqual(persisted["water_quality_source"].unique().tolist(), ["simulation"])
            reopened.close()

    def test_anomaly_location_filter_uses_070_threshold(self):
        movements = pd.DataFrame({
            "route_index": [0, 1, 2],
            "gps_lat": [12.1, 12.2, 12.3],
            "gps_lon": [77.1, 77.2, 77.3],
            "ph": [7.2, 7.3, 7.4],
            "turbidity": [12.0, 12.2, 12.4],
            "salinity": [0.8, 0.81, 0.82],
            "anomaly_index": [0.69, 0.70, 0.71],
            "water_quality_source": ["simulation", "simulation", "simulation"],
        })
        flagged = threshold_anomalies(movements)
        self.assertEqual(ANOMALY_THRESHOLD, 0.70)
        self.assertEqual(flagged["route_index"].tolist(), [2])


if __name__ == "__main__":
    unittest.main()
