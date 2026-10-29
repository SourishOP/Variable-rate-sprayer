# SYSTEM DESIGN AND METHODOLOGY

## 4.1 SYSTEM ARCHITECTURE

The system has five stages that run one after another for every spray
decision: image capture, disease classification, severity segmentation,
dose and timing calculation, and spray actuation. Figure 4.1 shows these
stages as a block diagram, and Figure 4.2 shows the same cycle as a
flowchart with the decision points made explicit.

{{FIG:block_diagram|figures/fig_block_diagram.png|System block diagram showing the five stages of one spray cycle.}}

{{FIG:cycle_flowchart|figures/fig_cycle_flowchart.png|Flowchart of one complete spray decision cycle, from trigger to valve actuation.}}

Figure 4.3 shows the same system as layers: the sensing layer (camera and
trigger), the processing layer (CNN classifier, segmentation model, dose
logic, all running on the cloud server), the communication layer
(WiFi, HTTP, serial link, Blynk), and the actuation layer (relay, solenoid
valve, pump, nozzle).

{{FIG:layered_architecture|figures/fig_layered_architecture.png|Layered view of the system: sensing, processing, communication and actuation.}}

## 4.2 ONE SPRAY CYCLE, STEP BY STEP

1. A trigger starts the cycle: a push button on the ESP32-CAM, a timer, or a
   remote command from the Blynk dashboard.
2. The ESP32-CAM captures a 640 by 480 pixel JPEG image through its OV2640
   sensor.
3. The ESP32-CAM sends the JPEG over WiFi as an HTTP POST request to the
   Flask `/predict` endpoint running on the cloud server.
4. The server runs the EfficientNetV2-B0 classifier on the image and returns
   the predicted disease class and a confidence score.
5. The server runs the U-Net segmentation model (or, if that model cannot be
   loaded, a classical colour based method) to find the diseased pixels and
   the leaf pixels, and computes the severity percentage.
6. The server maps the severity percentage to a category and a base
   coefficient, scales the coefficient by a disease specific factor to get
   the effective coefficient, and computes the chemical dose per hill and
   the valve open time.
7. The server returns a JSON response with all of the above fields to the
   ESP32-CAM.
8. The ESP32-CAM maps the category to a single digit code (0 for Healthy, 1
   for Low, 2 for Medium, 3 for High) and sends that digit over a serial
   link to the Arduino Nano. At the same time it updates the Blynk dashboard
   and lights the matching status LED.
9. The Arduino Nano looks up (or, in the full design, recomputes) the valve
   open time for the received code, and drives the relay, which switches
   the 12 V solenoid valve open for that duration. A code of 0 (Healthy)
   results in no actuation at all.
10. The system returns to waiting for the next trigger.

## 4.3 DATASETS

Two public datasets were combined to train the deployed six class
classifier: an open rice leaf disease dataset from the UCI repository,
contributing the Bacterial_Blight, Brown_Spot and Leaf_Smut classes (55
images in each of the two thin classes, see Chapter 9 for the exact test
numbers), and an open rice disease dataset hosted on HuggingFace,
contributing the Healthy (1,488 images), Blast (977 images), Neck_Blast
(1,000 images) and Brown_Spot (667 images, added to the UCI brown spot
images) classes. Combining the two datasets gives six classes in total and
removes a problem seen while training on the UCI set alone, where a fully
healthy leaf had no class of its own and could be wrongly pushed toward one
of the three disease labels. Figure 4.4 shows the class distribution of the
merged training set, and Figure 4.5 shows one real sample image from each of
the available Capstone test folders.

{{FIG:class_distribution|figures/fig_class_distribution.png|Class distribution of the merged six class training set.}}

{{FIG:samples_montage|figures/fig_samples_montage.png|Sample leaf images from the Capstone test set, one row per class.}}

The two thin classes, Bacterial_Blight and Leaf_Smut, have only 55 training
images each, far fewer than the other four classes. This imbalance is a
known limitation of the merged dataset and is addressed with class weighting
during training (Chapter 6) and discussed again in Chapter 9.

The lesion segmentation model is trained separately on PlantSeg (Wei et al.,
2024), a large, in the wild dataset of 11,400 diseased plant images and
8,000 healthy plant images with pixel level masks, downloaded from the open
Zenodo record for this project. PlantSeg covers many crop species beyond
paddy; using it to train a general lesion segmenter, rather than training a
paddy specific segmenter from scratch on a much smaller dataset, was a
deliberate design choice given the limited amount of pixel level paddy
lesion data available.

## 4.4 CLASSIFICATION MODEL

The disease classifier is EfficientNetV2-B0, used with transfer learning:
the backbone is initialised from ImageNet weights and then fine tuned on the
merged six class rice dataset. EfficientNetV2-B0 was chosen over a larger
backbone, such as a full sized ResNet or VGG network, because it reaches
competitive accuracy with far fewer parameters, which keeps inference fast
enough for the cloud hosted, real time use case this project needs
(consistent with the lightweight backbone choices reported by Sethy et al.,
2020, and Rahman et al., 2020, in Chapter 2). Figure 4.6 shows the
classifier's architecture at a high level: an input image resized to the
network's expected size, the EfficientNetV2-B0 backbone, and a final dense
softmax layer with six outputs, one per class.

{{FIG:classifier_architecture|figures/fig_classifier_architecture.png|EfficientNetV2-B0 classifier architecture, input to six class softmax output.}}

Training used class weighting to reduce the effect of the two thin classes
on the loss function, and standard image augmentation (random rotation,
flip and brightness and contrast changes) to make the model more robust to
the kind of variation seen in field photographs. Measured training and
validation accuracy curves and the confusion matrices are presented with
the numbers in Chapter 9.

## 4.5 SEVERITY ESTIMATION

Severity is measured, not estimated from the classifier's confidence. A
segmentation model marks each pixel of the leaf image as leaf or background,
and each leaf pixel as diseased or healthy. Severity is then

```
severity_percent = 100 * diseased_pixels / leaf_pixels
```

The segmentation step uses a U-Net architecture with a MobileNetV2 encoder,
trained with a combined Dice and binary cross entropy loss, which is a
common and effective loss choice for the heavily imbalanced, mostly healthy
pixel masks typical of lesion segmentation. Figure 4.7 shows the severity
pipeline from the input leaf image through to the severity percentage.

{{FIG:severity_pipeline|figures/fig_severity_pipeline.png|Severity pipeline: leaf isolation, lesion segmentation, pixel counting, severity percentage.}}

Before segmentation runs, the leaf itself must be separated from the
background, because a cluttered field photograph can otherwise have
background pixels wrongly counted as leaf or as disease. Two methods are
available for this leaf isolation step: MobileSAM, a lightweight version of
the Segment Anything Model, run automatically or from a box the user drags
over the leaf; and a free form polygon, drawn by the user tracing the leaf
outline by hand, used when the automatic method fails on a difficult
background. If the trained segmentation model itself cannot be loaded, the
system falls back to a classical colour based threshold method for finding
diseased pixels, so that a severity number is still produced (NFR5 in
Chapter 3).

## 4.6 DOSE AND SPRAY TIME EQUATIONS

Severity maps to one of four categories using fixed thresholds, each with a
base reduction coefficient, as implemented in the deployed severity module:

{{TABLE:severity_categories|Severity category thresholds and base coefficients, as implemented.}}
| Severity S (percent) | Category | Base coefficient (C_base) |
|---|---|---|
| 0 (classifier predicts Healthy), or measured severity below the 1.5 percent floor | Healthy | 0.00 |
| 0.1 to 5.0 | Low | 0.30 |
| 5.1 to 20.0 | Medium | 0.55 |
| above 20.0 | High | 0.80 |

The base coefficient is then scaled by a factor that depends on the
diagnosed disease, because some diseases are treated as needing a
proportionally higher dose at the same severity level:

{{TABLE:disease_factors|Per disease scaling factor applied to the base coefficient.}}
| Disease | Factor |
|---|---|
| Healthy | 0.00 |
| Leaf_Smut | 0.80 |
| Brown_Spot | 1.00 |
| Blast | 1.15 |
| Bacterial_Blight | 1.20 |
| Neck_Blast | 1.25 |

The effective coefficient is `C_eff = clamp(C_base x disease_factor, 0, 1)`,
clamped so it cannot exceed 1.00 even for the highest severity, highest
factor combination. The chemical dose per hill and the solenoid open time
then follow the equations used in the base paper (Tewari et al., 2020, Eqs.
4 and 5), with the open time standardised to a realistic valve window:

```
a  = (C_eff x A) / (d x 10)              # chemical per hill, mL/hill
ts = t_min + C_eff x (t_max - t_min)     # solenoid open time, seconds
```

where `A` is the recommended application rate in L/ha (design value 500),
`d` is the hill density in hills per square metre (design value 25), and
`t_min` and `t_max` define the valve's safe open time window (0.5 and 3.0
seconds). Using a fixed window for `ts`, instead of the base paper's
`ts = a / Qs` divide by flow rate, keeps the valve open time inside a safe,
known range regardless of the exact flow rate, which matters because the
real flow rate `Qs` depends on the physical pump and solenoid and is only
known once the hardware is calibrated (Chapter 5, Chapter 8). Section 9.6
reports dose and valve time worked examples using the design value of `Qs`
until a measured value is available, and compares the two dosing
conventions used in the base paper and in our implementation.

Two safeguards are applied before this calculation. First, if the
classifier's top confidence score is below 0.70, the prediction is flagged
as low confidence rather than acted on with full certainty (FR7). Second, if
the measured severity is below a floor of 1.5 percent of the leaf area, the
leaf is treated as Healthy even if the classifier predicted a disease class,
because a severity reading that small is more likely to be noise or a few
stray dark pixels than a genuine infection (FR8).

## 4.7 DESIGN DIAGRAMS

Figure 4.8 and Figure 4.9 show the data flow diagram (DFD) for the system at
level 0 (the system as a single process exchanging data with its external
entities) and level 1 (the system broken into its main internal processes).

{{FIG:dfd_level0|figures/fig_dfd_level0.png|Data flow diagram, level 0.}}

{{FIG:dfd_level1|figures/fig_dfd_level1.png|Data flow diagram, level 1, showing the main internal processes.}}

Figure 4.10 shows the use case diagram, covering the two actors relevant to
the system, the farmer or panel reviewer who uploads an image or watches the
dashboard, and the ESP32-CAM device that triggers a cycle automatically in
the field.

{{FIG:use_case|figures/fig_use_case.png|Use case diagram for the farmer or reviewer actor and the ESP32-CAM device actor.}}

Figure 4.11 shows the sequence diagram for one spray cycle, matching the
steps listed in section 4.2, and Figure 4.12 shows the module or class level
diagram, grouping the software into the Flask API layer, the model
inference layer (classifier and segmenter), the severity and dosing logic,
and the firmware layer (ESP32-CAM and Arduino Nano).

{{FIG:sequence|figures/fig_sequence.png|Sequence diagram for one spray cycle.}}

{{FIG:module_diagram|figures/fig_module_diagram.png|Module and class level diagram of the software.}}

## 4.8 CONSTRAINTS AND DESIGN TRADE OFFS

Cloud inference was chosen over on device inference because the trained
EfficientNetV2-B0 and U-Net models are too large and too slow to run
directly on an ESP32 class microcontroller within the project's time frame;
the trade off is that the system needs a working WiFi connection in the
field, which is recorded as a limitation (Chapter 9) and a future work item
(Chapter 10, on device TensorFlow Lite inference). A standardised valve open
time window was chosen over the base paper's direct divide by flow rate
formula so the valve timing stays safe and bounded before the flow rate is
calibrated on the actual hardware; this is a deliberate departure from the
base paper, discussed in section 4.6 and again in Chapter 9. Finally, a
single, general purpose lesion segmenter trained on PlantSeg was chosen over
a paddy specific segmenter trained from scratch, because PlantSeg is large
enough to train a reasonable segmentation model while no comparably sized
pixel level paddy lesion dataset was available; the trade off, a drop in
segmentation accuracy compared with a dataset built specifically for paddy,
is discussed with the measured IoU and Dice numbers in Chapter 9.
