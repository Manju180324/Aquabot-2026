from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data"
DEFAULT_TELEMETRY_PATH = DATA_DIR / "boat_sensor_data.csv"
WATER_QUALITY_DB_PATH = DATA_DIR / "water_quality_sim.db"
NAVIGATION_MISSIONS_DB_PATH = DATA_DIR / "navigation_missions.db"
APP_TITLE = "AquaBot Intelligence Command"
