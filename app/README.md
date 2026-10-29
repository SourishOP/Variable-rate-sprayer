# app: Flask server and web UI

The PaddyGuard demo. A Flask backend serves a single-page UI and a `/predict`
API that the ESP32-CAM also calls.

| File | Purpose |
|------|---------|
| `server.py` | Flask backend: `GET /` (UI), `GET /health`, `POST /predict` |
| `static/index.html` | Drag-and-drop UI: mask overlay, disease, severity formulas, valve animation, history tab |
| `launch_colab.py` | Starts the server in Colab and prints a public ngrok URL |
| `requirements.txt` | Dependencies for the server |

## Run

From the repository root (after `git lfs pull` so the models are present):

```bash
pip install -r app/requirements.txt
python app/server.py          # open http://127.0.0.1:5000
```

`/predict` accepts a multipart `image` field or raw bytes, and returns JSON with
`disease_class`, `confidence`, `severity_percent`, `category`,
`spray_time_s`, `spray_params` and a base64 `overlay_png`. The ESP32-CAM sends
raw RGB565 frames with `?fmt=rgb565&w=<w>&h=<h>`.

## Receiving images from the ESP32-CAM

The same command serves the ESP32-CAM. The server listens on `0.0.0.0` (all interfaces), port 5000, so the board can reach it at `http://<computer-ip>:5000/predict` if both are on the same network and the firewall allows TCP 5000. Check `/health` shows `mode: model` first. The full step-by-step setup, firewall command and troubleshooting table are in the [main README](../README.md#run-the-real-backend-for-esp32-cam-images).

## Modes

- **model**: `model/rice_disease_effnetv2b0.keras` is found and used.
- **demo**: no classifier file. The disease label is a heuristic, but severity is
  still measured from the mask.

## Configuration (environment variables)

| Variable | Default | Meaning |
|----------|---------|---------|
| `MODEL_PATH` | `model/rice_disease_effnetv2b0.keras` | Classifier weights |
| `CLASS_NAMES_PATH` | `model/class_names.txt` | Class order |
| `APP_RATE_LPH` | 500 | Application rate A (L/ha) |
| `HILL_DENSITY` | 25 | Hill density d (hills/m2) |
| `FLOW_RATE_MLS` | 3.5 | Pump flow rate Qs (mL/s), design value |

Interactive leaf isolation with MobileSAM needs `ultralytics` (included in
`requirements.txt`); without it the app falls back to the colour leaf mask.

When the ESP32-CAM calls `/predict`, the server writes `predict_debug.log` and
`last_esp32_frame.png` in this folder. Both are git-ignored.

Back to the [main README](../README.md).