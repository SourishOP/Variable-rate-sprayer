# SOFTWARE IMPLEMENTATION

## 6.1 OVERVIEW

This chapter describes how the software was actually built: the training
pipeline for the classifier and the segmentation model, the severity and
dosing module, the inference API, and the web demonstration interface. All
descriptions in this chapter are taken directly from the project's own code
(`model/`, `app/`) and from the notebooks used to train the models.

## 6.2 TRAINING PIPELINE

### 6.2.1 Classifier training

The classifier is trained in `model/colab_train_merged.py`, run on Google
Colab with a GPU. Training uses the merged six class dataset described in
Chapter 4 (section 4.3), split 80 percent training and 20 percent validation
with a fixed random seed so the split is repeatable. Images are resized to
the input size expected by EfficientNetV2-B0, and standard augmentation
(random rotation, horizontal flip, brightness and contrast changes) is
applied to the training split only. Training proceeds in two stages: first
with the EfficientNetV2-B0 backbone frozen, training only the new
classification head, then with the backbone unfrozen for fine tuning at a
lower learning rate. Class weights are applied during training to reduce
the effect of the two thin classes, Bacterial_Blight and Leaf_Smut (55
training images each), on the loss function.

### 6.2.2 Segmentation model training

The segmentation model is trained in `model/colab_train_segmenter.py` on the
PlantSeg dataset. The model is a U-Net with a MobileNetV2 encoder, trained
with a combined Dice and binary cross entropy loss, using the PlantSeg
training split and evaluated on its own validation split (1,247 images).
The output is a per pixel probability map, thresholded at 0.5 to produce a
binary lesion mask, as described in section 4.5.

### 6.2.3 Saved model artefacts

Training produces two Keras model files that are loaded at inference time:
`model/rice_disease_effnetv2b0.keras` (the classifier) and
`model/lesion_segmenter.keras` (the segmenter), together with
`model/class_names.txt`, which lists the six class names in the order the
classifier's output layer uses them, and `model/mobile_sam.pt`, the
MobileSAM weights used for interactive leaf isolation.

## 6.3 SEVERITY MODULE

`model/severity.py` is the single place where the severity, category,
dosing and timing logic described in Chapter 4 (sections 4.5 and 4.6) is
implemented. Its main functions are:

- `severity_to_category()`, which maps a severity percentage to one of
  Healthy, Low, Medium or High and returns the matching base coefficient,
  using the thresholds in Table 4.1 (`<= 0` percent Healthy, `0 to 5`
  percent Low with C_base 0.30, `5.1 to 20` percent Medium with C_base 0.55,
  `above 20` percent High with C_base 0.80).
- a disease factor lookup, `DISEASE_TREATMENT_FACTOR`, holding the per
  disease scaling factors listed in Table 4.2.
- effective coefficient logic, which multiplies the base coefficient by the
  disease factor and clamps the result between 0 and 1.
- a severity floor check, `MIN_SEVERITY_PERCENT` (default 1.5 percent),
  which forces the Healthy category even when the classifier predicted a
  disease, if the measured severity is below this floor.
- a confidence gate, `MIN_CONFIDENCE` (default 0.70), which sets a
  `low_confidence` flag on the output when the classifier's top score is
  below this value.
- dose and timing functions implementing
  `a = C_eff x A / (d x 10)` and the standardised `ts` window
  (`SPRAY_TS_MIN` = 0.5 s, `SPRAY_TS_MAX` = 3.0 s), described in section 4.6.
- `_load_seg_model()`, which loads the trained segmenter if the file is
  present and loadable, and otherwise falls back to a classical colour
  based threshold method, so severity measurement never fails outright
  (NFR5 in Chapter 3).

The output of the severity module is a dictionary carrying ten fields:
`disease_class`, `confidence`, `severity_percent`, `category`,
`category_code`, `base_coefficient`, `disease_factor`,
`reduction_coefficient`, `low_confidence`, and `note` (a short, human
readable explanation, for example that a severity floor forced the Healthy
category). All ten fields are returned by every call, and this exact field
set is confirmed by a passing unit test (U6.1, Chapter 8).

## 6.4 INFERENCE API

`app/server.py` is a Flask application exposing the following endpoints:

- `GET /health`, returning the server status, the mode (whether the real
  trained model or a demo fallback is loaded) and the list of class names.
- `GET /`, serving the static web demo page (`app/static/index.html`).
- `POST /predict`, accepting a multipart image upload, ordinary JPEG or PNG
  bytes in the request body, or a raw RGB565 frame with the query
  parameters `fmt=rgb565`, `w` and `h` (matching what the ESP32-CAM
  firmware sends, since the camera module on the real board has no
  hardware JPEG, Chapter 5, section 5.6.1), running the classifier and the
  severity module, and returning the JSON result described in section 6.3.
  A fourth query parameter, `overlay=0`, skips the large base64 mask image
  in the response for callers, such as the ESP32-CAM, that do not need it
  and cannot hold it in memory. Query parameters `A`, `d` and `Qs` let the
  caller override the default dosing constants for a given request, so the
  same API can be used with design values or with measured hardware values
  without changing code.
- The response always carries a `spray_time_s` value inside the
  `SPRAY_TS_MIN` to `SPRAY_TS_MAX` window, or 0 if the effective coefficient
  is 0 (Healthy).

The server is designed to run either locally (`python app/server.py`, for
the web demo and for development and the mode used with the ESP32-CAM
during the bring up session in Chapter 5, section 5.8.2, with the laptop
and the ESP32-CAM joined to the same mobile hotspot) or on Google Colab
with an ngrok tunnel (Chapter 5, section 5.7), since the ngrok tunnel gives
the Colab notebook a public URL the ESP32-CAM can reach over the internet
when the laptop and the board cannot share a local network.

## 6.5 WEB DEMONSTRATION INTERFACE

`app/static/index.html` is the web demo, branded "PaddyGuard", built with
plain HTML, CSS and JavaScript and served directly by the Flask server. The
page has three navigation tabs, Analyze, History and About, and the Analyze
tab is laid out as four numbered cards that walk through the same pipeline
described in Chapter 4:

1. An upload card showing the original image next to the segmented mask
   overlay, with a drag and drop area for picking a leaf photo.
2. A diagnosis card showing the predicted disease name, the confidence
   percentage, a severity gauge (marked at the 0, 5, 20 and 100 percent
   threshold points), the category badge, and the effective coefficient.
3. A "severity calculation (live)" card that shows the five calculation
   steps with the real numbers for the uploaded image: leaf area in pixels,
   diseased area in pixels, the ratio, the severity percentage, the base
   coefficient from the category, and the disease factor giving the
   effective coefficient.
4. A "variable rate spray, solenoid open time" card showing the dose
   equation `a = (C_eff x A) / (d x 10)` and the timing equation
   `ts = t_min + C_eff x (t_max - t_min)`, both filled in with the real
   numbers for the uploaded image, together with a small valve and hose
   animation and a large readout of the resulting `ts` value.

The History tab keeps a record of past analyses done in the same browser
session, and the About tab explains the project and the team. Figure 6.1
through Figure 6.4 are real screenshots of the running application, taken
by loading sample leaf images from `Capstone/Test/` into the live server.

{{FIG:ui_home|figures/ui_home.png|PaddyGuard web demo, home or upload view.}}

{{FIG:ui_result_brown_spot|figures/ui_result_brown_spot.png|PaddyGuard analysis result for a Brown Spot leaf image, showing the diagnosis, severity calculation and spray timing cards.}}

{{FIG:ui_result_neck_blast|figures/ui_result_neck_blast.png|PaddyGuard analysis result for a Neck Blast leaf image.}}

{{FIG:ui_history|figures/ui_history.png|PaddyGuard History tab, showing past analyses from the same session.}}

## 6.6 MODULE DESCRIPTION

Table 6.1 lists every software module used in the project, its file, and
its responsibility, matching the module diagram in Figure 4.12.

{{TABLE:module_description|Software module description.}}
| Module | File | Responsibility |
|---|---|---|
| Classifier trainer | model/colab_train_merged.py | Trains EfficientNetV2-B0 on the merged six class dataset |
| Segmenter trainer | model/colab_train_segmenter.py | Trains the U-Net lesion segmenter on PlantSeg |
| Severity and dosing logic | model/severity.py | Category mapping, disease factor, dose and timing equations, guards |
| Single image CLI prediction | model/predict.py | Command line tool to run one image through the classifier and severity module |
| Class names | model/class_names.txt | Ordered list of the six class names matching the classifier output |
| Inference API | app/server.py | Flask endpoints (/health, /, /predict) serving the trained models |
| Web demo page | app/static/index.html | PaddyGuard browser interface |
| Colab launcher | app/launch_colab.py | Starts the Flask server with an ngrok tunnel on Google Colab |
| ESP32-CAM firmware | firmware/esp32cam_sprayer.ino (Chapter 5, Appendix 4) | Captures the image, calls the API, forwards the spray command to the Nano, updates Blynk |
| Arduino Nano firmware | firmware/valve_controller.ino (Chapter 5, Appendix 4) | Actuates the relay and solenoid for the received duration, with a safety cap |
