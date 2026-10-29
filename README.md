# PaddyGuard: Variable-Rate Sprayer for Rice Leaf Disease

Deep learning and IoT based variable-rate chemical spraying for disease control
in paddy (rice) crops. A camera image of a rice leaf is classified for disease,
the diseased area is measured by segmentation, and the measured severity sets
how long a solenoid valve stays open, so healthy plants get no chemical and
heavily infected plants get more.

Capstone project BCE497J / BCSE497J, SCOPE, VIT Chennai. Authors: Sourish Das
(23BCE1179) and Aditya Singh (23BCE1293). Guide: Dr. Vergin Raja Sarobin M.

## Contents

- [How it works](#how-it-works)
- [Results](#results)
- [Repository layout](#repository-layout)
- [Quick start](#quick-start)
  - [Run the real backend for ESP32-CAM images](#run-the-real-backend-for-esp32-cam-images)
- [Hardware](#hardware)
- [Rebuilding the report](#rebuilding-the-report)
- [Project status and limitations](#project-status-and-limitations)
- [Datasets and references](#datasets-and-references)
- [Credentials and secrets](#credentials-and-secrets)
- [License](#license)

## How it works

```
ESP32-CAM  --RGB565 frame-->  Flask API (/predict)  --JSON-->  ESP32-CAM  --"S<ms>,<cat>"-->  Arduino Nano  -->  relay  -->  solenoid valve
                              1. EfficientNetV2-B0 classifies the disease
                              2. U-Net (optionally with MobileSAM leaf isolation) segments the lesions
                              3. severity % = 100 * diseased pixels / leaf pixels
                              4. severity level and disease factor give the dose and valve open time
```

![System block diagram](report/figures/fig_block_diagram.png)

| Severity % | Level | Base coefficient |
|------------|-------|------------------|
| Healthy (or below 1.5%) | Healthy | 0.00 |
| 0.1 - 5 | Low | 0.30 |
| 5.1 - 20 | Medium | 0.55 |
| above 20 | High | 0.80 |

The base coefficient is multiplied by a per-disease factor (Bacterial Blight
1.20, Neck Blast 1.25, Blast 1.15, Brown Spot 1.00, Leaf Smut 0.80). The valve
open time is limited to a 0.5 to 3.0 s window. Classes: `Bacterial_Blight`,
`Blast`, `Brown_Spot`, `Healthy`, `Leaf_Smut`, `Neck_Blast`. Details are in
[results/RESULTS.md](results/RESULTS.md) and
[docs/model_run_instructions.md](docs/model_run_instructions.md).

## Results

Measured on held-out validation data (see [results/RESULTS.md](results/RESULTS.md)):

| Component | Metric | Value |
|-----------|--------|-------|
| 6-class classifier (merged datasets) | Validation accuracy (815 images) | 83.80% |
| 3-class classifier (UCI paddy set) | Test accuracy (164 images) | 91.5% |
| Lesion segmenter (U-Net, PlantSeg) | Validation IoU / Dice (1,247 images) | 0.4450 / 0.5641 |
| Software tests | Unit tests / API tests | 37 of 37 / 13 of 13 passed |

![Confusion matrix of the merged classifier](results/confusion_matrix_merged.png)

Bacterial Blight and Leaf Smut have only 55 training images each, so they are
the weakest classes. Blast and Brown Spot are often confused with each other.

![Web UI](report/figures/ui_result_brown_spot.png)

## Repository layout

```
.
├── app/            Flask server and PaddyGuard web UI            -> app/README.md
├── model/          Inference code, training scripts, weights (LFS) -> model/README.md
├── notebooks/      Colab training notebooks                       -> notebooks/README.md
├── firmware/       ESP32-CAM and Arduino Nano sketches, Blynk     -> firmware/README.md
├── hardware/       Build plan, bill of materials, bench test log   -> hardware/README.md
├── data/           Sample leaf images for testing                  -> data/README.md
├── docs/           Run guide for training, prediction and demo     -> docs/README.md
├── results/        Metrics, charts, review presentations           -> results/README.md
├── report/         Final report sources, figures, built reports    -> report/README.md
├── scripts/        Helper scripts (chart generation)               -> scripts/README.md
├── LICENSE
└── README.md
```

## Quick start

Requirements: Python 3.11, [Git LFS](https://git-lfs.com) (the trained models
are stored with LFS).

```bash
git clone https://github.com/SourishOP/Variable-rate-sprayer.git
cd Variable-rate-sprayer
git lfs pull                       # downloads the .keras and .pt model files
```

Create a virtual environment and install the app dependencies.

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r app/requirements.txt
```

Linux / macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
```

Run the web demo and open <http://127.0.0.1:5000>:

```bash
python app/server.py
```

Predict on one image from the command line:

```bash
python model/predict.py --image data/sample_images/Brown_Spot/Brown_Spot_01.jpg
```

Without a model file the server starts in demo mode (heuristic disease label,
but severity is still measured from the mask). To train the models, open the
notebooks in [notebooks/](notebooks/README.md) on Google Colab with a GPU.

### Run the real backend for ESP32-CAM images

The web demo above is for uploading photos by hand. To receive and classify the
pictures that the ESP32-CAM captures, run the same backend (`app/server.py`) on a
computer that the ESP32 can reach over Wi-Fi. The server listens on all network
interfaces (`0.0.0.0`, port 5000), so no code change is needed. The tested setup is
a PC and the ESP32-CAM on the same network, for example a phone hotspot.

1. **Get the real models.** Run `git lfs pull`, then check that
   `model/rice_disease_effnetv2b0.keras` is a large file (about 41 MB), not a
   small text pointer. Install the dependencies as in the steps above.

2. **Start the server.**

   ```bash
   python app/server.py
   ```

   Use `PORT=8000 python app/server.py` (Linux/macOS) or
   `$env:PORT = "8000"; python app/server.py` (PowerShell) to change the port.

3. **Check that it runs in model mode.** Open <http://127.0.0.1:5000/health>. It
   must report `"model_loaded": true` and `"mode": "model"`. If it says
   `"demo"`, the classifier file is missing and ESP32 results will not be real.

4. **Find the computer's IP address on the shared network.**
   Windows: `ipconfig` (IPv4 Address of the Wi-Fi adapter).
   Linux/macOS: `ip addr` or `ifconfig`. Use this address, not `localhost`.

5. **Allow the port through the firewall.** On Windows, run once in an
   administrator PowerShell, otherwise the ESP32 cannot connect:

   ```powershell
   New-NetFirewallRule -DisplayName "PaddyGuard Flask 5000" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow -Profile Private
   ```

   Mark the Wi-Fi network as Private, or add `Public` to `-Profile` if you
   must use a public profile. On Linux: `sudo ufw allow 5000/tcp`.

6. **Test from another device** on the same network (a phone browser works):
   `http://<computer-ip>:5000/health` should return the same JSON.

7. **Point the ESP32-CAM at the server.** Copy
   `firmware/esp32cam_sprayer/secrets.h.example` to `secrets.h` and set
   `WIFI_SSID`, `WIFI_PASSWORD` and
   `PREDICT_URL "http://<computer-ip>:5000/predict"`. Flash the sketch (see
   [firmware/README.md](firmware/README.md)). If the computer's IP changes
   (reconnect or reboot), update `PREDICT_URL` and flash again.

8. **Trigger a capture.** Press the push button on GPIO13 (or the Blynk button
   if enabled). The ESP32 sends one raw RGB565 frame (320x240) to
   `POST /predict?fmt=rgb565&overlay=0&w=320&h=240` and waits for the JSON
   reply. In the server terminal you should see a `[predict] from=<esp-ip> ...`
   line for each capture.

What the server does with each frame, and what you can inspect:

| Item | Where |
|------|-------|
| Request log (client IP, format, byte count, decode errors) | server terminal and `app/predict_debug.log` |
| Last frame received from the ESP32, to check framing and colours | `app/last_esp32_frame.png` |
| Reply used by the ESP32 | `disease_class`, `confidence`, `severity_percent`, `category_code`, `spray_time_s` (JSON) |
| Valve command sent on to the Nano | `S<ms>,<cat>*<HH>` over serial, `<ms>` is `spray_time_s` in milliseconds |

Common problems:

| Symptom | Likely cause |
|---------|--------------|
| ESP32 prints connection or timeout errors | Wrong IP in `PREDICT_URL`, different network, or the firewall rule is missing |
| Nothing appears in the server terminal | The request never arrived, test `http://<computer-ip>:5000/health` from a phone |
| HTTP 400 `could not decode image` | Body size does not match `w` x `h` x 2 bytes, check the sketch frame size |
| Colours look swapped in `last_esp32_frame.png` | RGB565 byte order mismatch between firmware and server |
| Results always look like a demo | `/health` shows `"mode": "demo"`, run `git lfs pull` |
| First reply is slow | TensorFlow and the models load on first use. In the recorded API tests the median reply took about 0.76 s and the slowest 4.5 s (`report/content/api_test_results.json`) |

The server has no authentication. Run it only on a trusted local network, not
on the open internet. The tested path is plain HTTP on a local network. Hosting
the backend on Colab behind an ngrok HTTPS URL (`app/launch_colab.py`) works for
the web UI, but the current ESP32 sketch posts over plain HTTP and would need
changes for HTTPS.

## Hardware

AI-Thinker ESP32-CAM (capture and Wi-Fi), Arduino Nano (valve timing), 5 V
relay module, 12 V normally-closed solenoid valve, 12 V diaphragm pump, LM2596
buck converter, spray nozzle and silicone tubing. Planned budget is about
Rs. 2,250 to 2,400. The wiring, build phases and bill of materials are in
[hardware/hardware_implementation_plan.md](hardware/hardware_implementation_plan.md).
The ESP32 needs the backend running, see [Run the real backend for ESP32-CAM images](#run-the-real-backend-for-esp32-cam-images). To flash the boards, copy `firmware/esp32cam_sprayer/secrets.h.example` to
`secrets.h`, fill it in, and follow [firmware/README.md](firmware/README.md).

## Rebuilding the report

The report is generated from Markdown sources by Python scripts. See
[report/README.md](report/README.md). Built copies (DOCX and PDF) are in
`report/output/`.

## Project status and limitations

- The software chain (classifier, segmenter, severity, dosing, web UI, Flask
  API) is complete and tested.
- On hardware, the ESP32-CAM and Arduino Nano are flashed and bench tested on USB
  power, including a dry run of the relay and valve. The full liquid path with
  the pump and a battery powered run were not done. The pump flow rate Qs is the
  design value of 3.5 mL/s, not a measured one. See
  [hardware/HARDWARE_TEST_DATA.md](hardware/HARDWARE_TEST_DATA.md) and
  [report/OPEN_ITEMS.md](report/OPEN_ITEMS.md).
- Bacterial Blight and Leaf Smut need more training data.
- The 0.5 to 3.0 s spray window is a research-based default, not calibrated to
  a specific pump and nozzle.

## Datasets and references

- Paddy Leaf Disease (UCI), Kaggle `badhon7432/paddyleafdiseaseuci`.
- An open HuggingFace rice leaf set, merged in for Healthy, Blast and Neck Blast
  (see `model/colab_train_merged.py`).
- PlantSeg (Wei et al., 2024), Zenodo record
  [14935094](https://zenodo.org/records/14935094), used for lesion
  segmentation. Check its license terms before reuse.
- Base paper: Tewari et al. (2020), *Image processing based real-time
  variable-rate chemical spraying system for disease control in paddy crop*,
  Artificial Intelligence in Agriculture, 4, 21-30.
- MobileSAM, run through the `ultralytics` package.

The full reference list is in [report/content/references.json](report/content/references.json).
The images in `data/sample_images/` come from the public datasets above and
keep their original licenses.

## Credentials and secrets

No credentials are stored in this repository. Wi-Fi, server URL and Blynk
values go in `firmware/esp32cam_sprayer/secrets.h` (git-ignored), and Kaggle
tokens go in an environment variable (`KAGGLE_API_TOKEN`).

## License

Code is released under the [MIT License](LICENSE). Datasets, papers and model
backbones keep their own licenses.
