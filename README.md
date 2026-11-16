# AquaBot Intelligence Command Center

A Streamlit dashboard for recorded AquaBot telemetry, YOLO waste detection, and a separate simulated water-quality patrol. It distinguishes recorded data from simulation and does not connect to or control a physical vehicle.

## Start the application on Windows

### Application directory

Run the app from the folder containing `app.py` and `requirements.txt`:

`C:\Users\manju\OneDrive\Documents\NHCE\SEM- 6\Intelligence_Aqua_Bot_15th_may\Intelligence_Aqua_Bot\Intelligence Aqua Bot`

Open PowerShell and change to that exact folder:

```powershell
Set-Location -LiteralPath 'C:\Users\manju\OneDrive\Documents\NHCE\SEM- 6\Intelligence_Aqua_Bot_15th_may\Intelligence_Aqua_Bot\Intelligence Aqua Bot'
```

### Install and launch

This project includes a virtual environment named `venv`. Install the listed dependencies and launch Streamlit from the application directory:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m streamlit run app.py
```

Streamlit prints a **Local URL**, normally `http://localhost:8501`. Open it in your browser and leave the PowerShell process running while using the app. Press Ctrl+C in that terminal to stop it.

If the included `venv` folder is missing, create it first:

```powershell
py -3.10 -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m streamlit run app.py
```

You can optionally activate the environment with these PowerShell commands:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The execution-policy change applies only to the current PowerShell process. The direct executable commands above avoid activation-policy issues.

## How the website works

The sidebar has four destinations:

1. **Analytics** loads the included CSV by default or a CSV uploaded in the sidebar. It parses timestamps and numeric fields, requires valid timestamps and GPS to keep a route row, and reports rejected rows. Recorded sensor cards, date filtering, trends, comparisons, sampling frequency, missing-value information, row inspection, and filtered CSV download are provided. Additional tabs contain the water-quality simulation and pipeline/data-quality summary.
2. **Navigation animation** plays through the ordered GPS recording. Start/Resume advances along route rows, Pause holds the current point, Stop ends playback, Reset starts a fresh route playback, and the slider can reposition the vehicle. The AUV illustration follows its GPS position and heading and displays completed/upcoming route segments. This is recorded-data playback, not live navigation or hardware control.
3. **Waste detection data** accepts an image from the camera or an image upload, runs the selected included YOLO weights, and displays the detected label/category, confidence, inference time, and session totals. Waste categories are heuristic mappings of generic YOLO labels; these weights are not a marine-waste-trained model.
4. **Mission reports** displays persistent navigation logs and session-based camera-detection history. Navigation logs can be downloaded as CSV or PDF. Detection history can be exported as a separate PDF when `fpdf` is installed.

### Navigation logging and simulated chemistry

When navigation playback advances, every crossed route row is stored in `data/navigation_missions.db`. GPS coordinates and optional local x/y and speed are taken from that recorded telemetry row. The supplied route CSV has no pH, turbidity, or salinity fields. To provide readings at each mapped location, the app maps each GPS position onto a 12×12 simulation grid and generates fresh, spatially based pH/turbidity/salinity values with per-sample variation. The logged `water_quality_source` is `simulation`; these are not physical sensor values. Replaying a route as a new mission generates new simulated readings.

### Composite anomaly score

Each simulated chemistry reading is compared with that run's baseline. The absolute pH, turbidity, and salinity deviations are expressed in baseline standard-deviation units and averaged with equal weights into raw score $R$. The displayed composite score is $S=R/(1+R)$, which is bounded by $0\le S<1$. Waste Detection Data marks logged route coordinates when $S>0.70$. Existing raw scores in the navigation database are converted to the bounded scale on database initialization.

The separate Analytics water-quality simulation preserves the Tkinter engine's generated grid, sampled baseline, heuristic patrol movement, run-derived 95th-percentile score threshold, and anomaly persistence. Its database is `data/water_quality_sim.db`; initialization creates missing tables and does not drop existing tables.

## Data sources and limitations

The included `data/boat_sensor_data.csv` fields are `timestamp`, `x`, `y`, `speed`, `ultrasonic`, `gps_lat`, `gps_lon`, `lora_rssi`, and `lora_snr`. A custom uploaded CSV needs `timestamp`, `gps_lat`, and `gps_lon` for route playback; other numeric fields are discovered for analytics. The supplied CSV does not document units for speed, ultrasonic, or LoRa measurements, so the dashboard does not invent units or thresholds.

Battery, depth, temperature, humidity, and physical pH/turbidity/salinity sensors are not provided. Camera-based distance proxy and roll are simulated. Steering suggestions and route controls are visual demonstrations only; there is no hardware-control link. CSV anomaly detection and pipeline-stage durations are not implemented, so those metrics are reported as unavailable rather than fabricated. An optional Groq assistant dependency is listed, but it is not one of the four dashboard pages.

## Project structure

- `app.py` — Streamlit startup, shared data loading, and the four-page navigation
- `components/` — shared UI helpers and visual theme
- `pages/` — Analytics, Navigation animation, Waste detection data, and Mission reports
- `services/` — telemetry parsing, navigation logging, anomaly scoring, YOLO, reports, and simulation logic
- `visualizations/` — animated AUV route, Plotly charts, simulation grid, and anomaly map
- `config/` — application paths and settings
- `assets/` — AquaBot SVG artwork
- `data/` — supplied telemetry CSV and generated SQLite databases
