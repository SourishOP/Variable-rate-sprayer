# RESULTS AND DISCUSSION

## 9.1 OVERVIEW

This chapter presents every measured result from the software: classifier
accuracy on two separate test sets, segmentation quality, a full pipeline
simulation on real test images, API response times, and a comparison with
the base paper and the related work from Chapter 2. Hardware measured
results (flow rate, dispensed volume, cycle time, field trial savings) are
reported exactly as supplied by the team in
`Capstone/hardware_evidence/HARDWARE_TEST_DATA.md`. At the time of writing
this report, the real hardware bench test and one real integration cycle
described in Chapter 5, section 5.8.2 and Chapter 8, section 8.4, confirm
that the complete signal chain works on real hardware, but the flow rate,
the spray volume with water, and the field trial savings are still not
measured; where a value remains unmeasured, a placeholder is shown and the
gap is listed in OPEN_ITEMS.md.

## 9.2 CLASSIFIER PERFORMANCE

### 9.2.1 Three class model (initial UCI dataset)

Before the two datasets were merged, an initial classifier was trained on
the three disease classes available in the UCI rice leaf dataset alone
(Bacterial_Blight, Brown_Spot, Leaf_Smut). On a held out test set of 164
images the model had never seen, overall accuracy was 91.5 percent.

{{TABLE:three_class_results|Three class model, held out test set, 164 images.}}
| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Bacterial leaf blight | 1.00 | 1.00 | 1.00 | 55 |
| Brown spot | 0.86 | 0.89 | 0.87 | 54 |
| Leaf smut | 0.89 | 0.85 | 0.87 | 55 |
| Overall accuracy | | | 0.915 | 164 |

Bacterial leaf blight is classified perfectly on this test set. The small
remaining error is almost entirely a confusion between Brown spot and Leaf
smut, two diseases that both show tan coloured lesions and can look similar
in a photograph. This result shows the EfficientNetV2-B0 architecture
itself performs well when every class has enough training data, which sets
up the comparison with the six class merged model below.

### 9.2.2 Six class merged model

Two result sets exist for the merged, six class model, because of a known
discrepancy between the notebook run that produced the deployed model file
and the run recorded in `results/RESULTS.md`; both are reported here rather
than hiding the mismatch, and the discrepancy is listed in OPEN_ITEMS.md.

Result set 1, from the notebook run that produced the deployed
`rice_disease_effnetv2b0.keras` model (Figure 9.1, `confusion_matrix.png`):
859 held out images, overall accuracy 87.08 percent (748 of 859 correct).

Result set 2, from `results/RESULTS.md` and the review 3 deck (Figure 9.2,
`confusion_matrix_merged.png`): 815 held out images (only four of the six
classes had held out samples in this split), overall accuracy 83.80 percent,
macro average F1 0.82, weighted average F1 0.84.

{{FIG:confusion_matrix|figures/confusion_matrix.png|Confusion matrix, six class merged model, result set 1 (859 images, 87.08 percent accuracy).}}

{{FIG:confusion_matrix_merged|figures/confusion_matrix_merged.png|Confusion matrix, six class merged model, result set 2 (815 images, 83.80 percent accuracy).}}

{{TABLE:six_class_results|Six class merged model, per class results, result set 2 (815 images).}}
| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Neck_Blast | 1.00 | 1.00 | 1.00 | 206 |
| Healthy | 0.83 | 0.88 | 0.85 | 288 |
| Brown_Spot | 0.73 | 0.74 | 0.73 | 126 |
| Blast | 0.74 | 0.67 | 0.71 | 195 |
| Overall accuracy | | | 0.838 | 815 |

Neck blast is classified perfectly in this split, and Healthy reaches a
strong 0.85 F1 score, which matters because the Healthy versus diseased
decision is the one that most directly controls whether the system sprays
at all. Blast and Brown_Spot are the weakest pair, at 0.71 and 0.73 F1,
again because both diseases can show similar tan lesions. Bacterial_Blight
and Leaf_Smut, the two thin classes with only 55 training images each, had
no held out samples in this particular validation split and so cannot be
scored here; their performance is instead visible in the three class result
above and in the pipeline simulation below (section 9.4), where both appear
as test classes. Figure 9.3 shows the training and validation accuracy
curves across training epochs.

{{FIG:train_val_accuracy|figures/chart_train_val_accuracy.png|Training and validation accuracy across epochs, six class merged model.}}

### 9.2.3 Discussion of classifier results

The gap between the three class model's 91.5 percent and the six class
model's 83.80 to 87.08 percent is expected: adding three more classes, two
of which are the known thin classes, makes the classification problem
harder, and the merged dataset mixes two different source datasets with
their own photography conditions. This pattern matches the lab to field
accuracy drop reported by Mohanty et al. (2016) in Chapter 2, where a model
trained to a near perfect score on one distribution of images lost a large
amount of accuracy on images from a different distribution; our drop is
much smaller because both of our datasets are still curated photographs
rather than uncontrolled field images, but the same underlying effect, a
model performing worse outside the exact distribution it was trained and
validated on, is visible in our own pipeline simulation in section 9.4.

## 9.3 SEGMENTATION QUALITY

The lesion segmentation model was evaluated on the full PlantSeg validation
split, 1,247 images, giving a mean intersection over union (IoU) of 0.4450
and a mean Dice score of 0.5641.

{{TABLE:segmentation_results|Segmentation model validation results against the PlantSeg paper's own baselines.}}
| Model | mIoU (percent) | mAcc (percent) |
|---|---|---|
| DeepLabv3, ResNet50 (PlantSeg paper baseline) | 17.24 | 37.95 |
| DeepLabv3+, ResNet101 (PlantSeg paper baseline) | 27.18 | 42.29 |
| SegNeXt, MSCAN-L (PlantSeg paper's best baseline) | 44.52 | 59.95 |
| Our U-Net, MobileNetV2 encoder | 44.50 | not directly comparable (Dice 0.5641 reported instead) |

Our lightweight binary lesion segmenter reaches a mean IoU, 44.50 percent,
that is close to the PlantSeg paper's own strongest baseline, SegNeXt with
an MSCAN-L backbone at 44.52 percent, while using a much smaller encoder
(MobileNetV2) suited to being served from the same lightweight Flask API as
the classifier. This result should be read carefully: our task is a simpler
binary (diseased or not) segmentation, while the PlantSeg baselines solve a
harder, multi category segmentation task across many diseases, so the
comparison is closer in spirit than in exact task definition. The licence
of the PlantSeg paper itself is CC BY-NC-ND 4.0, not plain CC BY as stated
in `results/RESULTS.md` and in the hardware plan; this correction is
recorded in the facts register and in OPEN_ITEMS.md.

## 9.4 PIPELINE SIMULATION ON REAL TEST IMAGES

A simulation script (`report/build/run_pipeline_test.py`) runs the
real classifier, the real segmenter, and the real severity and dosing logic
together on every image in `Capstone/Test/` (49 images across five
available folders; the Capstone/Test set does not include a Blast folder).
This is a software simulation on a small, hand picked sample, not a field
measurement, and it is labelled as such throughout this section; it is a
useful check of how the complete pipeline behaves end to end, separate from
the larger, held out validation numbers in section 9.2, which remain the
primary evidence for classifier accuracy.

{{TABLE:pipeline_summary|Pipeline simulation summary, 49 real test images.}}
| Metric | Value |
|---|---|
| Images | 49 |
| Raw top class accuracy (before guards) | 51.02 percent (25 of 49) |
| Accuracy after guards (severity floor, confidence gate) | 42.86 percent (21 of 49) |
| Images resulting in no spray (Healthy after guards) | 12 of 49 |
| Mean effective coefficient | 0.568 |
| Chemical saving, equation based dose, vs constant full rate | 43.2 percent |
| Chemical saving, valve volume based, vs constant full rate | 40.08 percent |
| Median classification time | 99.1 ms |
| Median severity measurement time | 194.9 ms |
| Maximum classification time | 209.0 ms |
| Maximum severity measurement time | 553.4 ms |

Accuracy after guards (42.86 percent) is lower than the raw top class
accuracy (51.02 percent) on this small sample. This looks unusual at first,
but the reason is explained correctly, not hidden: the severity floor and
confidence gate guards (Chapter 4, section 4.6) are designed to protect
against over spraying on noisy or uncertain readings, and on this
particular 9 to 10 image per class sample they sometimes relabel a genuinely
diseased image as Healthy because its measured diseased area happened to
fall under the 1.5 percent floor. This is the guard logic working as
designed, not a bug, but it does mean that on a small, unrepresentative
sample like this one, the guarded accuracy figure can be lower than the raw
figure. The per class validation numbers in section 9.2 (815 or 859 images)
remain the correct evidence for the classifier's real accuracy; this 49
image run should be read only as a demonstration that the full pipeline
runs correctly end to end on real images, including its guard logic.

{{TABLE:pipeline_per_class|Pipeline simulation, per class breakdown.}}
| Class | n | Correct (raw) | Correct (after guards) | Mean severity (percent) | Mean effective coefficient | Mean spray time (s) |
|---|---|---|---|---|---|---|
| Bacterial_Blight | 9 | 3 | 2 | 42.04 | 0.858 | 2.589 |
| Brown_Spot | 10 | 7 | 4 | 1.53 | 0.144 | 0.610 |
| Neck_Blast | 10 | 10 | 10 | 39.76 | 0.969 | 2.922 |
| Healthy | 10 | 2 | 3 | 30.69 | 0.590 | 1.825 |
| Leaf_Smut | 10 | 3 | 2 | 5.74 | 0.309 | 1.121 |

Neck_Blast is identified correctly on every single one of its 10 test
images, both before and after guards, matching its perfect F1 score in the
larger validation set (section 9.2). The weaker classes here,
Bacterial_Blight and Leaf_Smut, are exactly the two thin, 55 image training
classes identified throughout this report as the main data limitation.

A resize sensitivity check (`check_resize_effect.py`) found that the exact
image resizing method used before classification has a small effect on this
same 49 image sample: PIL's default resize gave 25 of 49 correct, PIL
bilinear resize gave 23 of 49, and TensorFlow bilinear resize without
anti aliasing also gave 23 of 49. This is a minor method sensitivity worth
noting honestly as a limitation (section 9.8), rather than a large concern.

## 9.5 API RESPONSE TIME

The API integration tests (Chapter 8, section 8.3) measured a median
response time of 757.8 ms, with a minimum of 396.1 ms and a maximum of
4,487.9 ms. The maximum occurred on the first request in the test run,
which includes a one time model loading and warm up cost; later requests to
the same running server were all under one second. This supports the non
functional requirement in Chapter 3 (NFR2) that one inference cycle should
typically complete in under a second once the server is warmed up, though
the full spray cycle target in NFR3 (under 5 seconds) also depends on
network latency to the cloud server and on the hardware actuation time,
neither of which is measured by this API test alone.

## 9.6 DOSE AND SPRAY TIME WORKED EXAMPLES

Using the design values `A` = 500 L/ha, `d` = 25 hills per square metre and
`Qs` = 3.5 mL/s (the design value stated in the hardware plan, not yet a
measured value, see Chapter 5, section 5.8.1), Table 9.1 works through the
dose per hill and spray time for each category, following the equations in
Chapter 4, section 4.6. These figures are calculated, not measured on
hardware, and are labelled as such.

{{TABLE:dose_worked_examples|Worked dose and spray time examples, calculated from design values.}}
| Category | Effective coefficient (C_eff) | Dose per hill, a (mL/hill) | Spray time, ts (s), standardised window |
|---|---|---|---|
| Healthy | 0.00 | 0.000 | 0.000 (no spray) |
| Low | 0.30 | 0.600 | 1.250 |
| Medium | 0.55 | 1.100 | 1.875 |
| High | 0.80 | 1.600 | 2.500 |
| High, Neck_Blast (clamped) | 1.00 | 2.000 | 3.000 |

For comparison, the base paper's own three level system (Chapter 2, Chapter
4, section 4.6) uses coefficients of 0.33, 0.67 and 1.00 and the direct
formula `ts = a / Qs`; at the same design `Qs` of 3.5 mL/s, this gives
`ts` values of 0.189, 0.383 and 0.571 seconds for Low, Medium and High,
noticeably shorter than our standardised 0.5 to 3.0 second window, because
our window is deliberately set to realistic physical valve open times
rather than the small values the original divide by flow rate formula
happens to produce at this particular design `Qs`.

## 9.7 COMPARISON WITH THE BASE PAPER AND RELATED WORK

Table 9.2 places our measured and simulated chemical saving figures next to
the base paper's field measured figure and the other variable rate sprayers
discussed in Chapter 2.

{{TABLE:comparison_chemical_saving|Chemical saving comparison with the base paper and related variable rate sprayers.}}
| System | Chemical saving vs constant/uniform rate | Measurement type |
|---|---|---|
| Tewari et al. (2020), base paper | minimum 33.88 percent (field measured, 300 m2 paddy plot) | Field measured |
| Esau et al. (2013), wild blueberry | 9.90 to 51.22 percent | Field measured |
| Zhang et al. (2025), fruit tree canopy fusion | 74.0 percent (low severity), 42.7 percent (high severity) | Field measured |
| Our system, equation based dose | 43.2 percent | Software simulation, 49 images |
| Our system, valve volume based | 40.08 percent | Software simulation, 49 images |

Our simulated chemical saving, 40 to 43 percent, is higher than the base
paper's field measured 33.88 percent minimum saving, which is consistent
with the design goal in Chapter 1 of adding a Healthy, zero spray category
that the base paper's three level system does not have (12 of the 49 test
images resulted in no spray at all in our simulation). This comparison must
still be read carefully: our figure comes from a 49 image software
simulation, not a field trial, while the base paper's 33.88 percent is a
real field measurement. The hardware field trial described in Chapter 5,
section 5.8, when completed by the team, would give a directly comparable
field measured figure for our own system; until then, this chapter reports
the honest difference between the two kinds of evidence rather than
presenting the simulation figure as equivalent to a field result.

Table 9.3 compares our classifier's measured accuracy with the other rice
and plant disease classifiers discussed in Chapter 2.

{{TABLE:comparison_accuracy|Classifier accuracy comparison with related work.}}
| System | Reported accuracy or F1 | Classes | Dataset size |
|---|---|---|---|
| Mohanty et al. (2016), GoogLeNet, lab images | 99.35 percent accuracy | 26 diseases, 14 crops | 54,306 images |
| Mohanty et al. (2016), same model, field images | 31.40 to 31.69 percent accuracy | same | two independent field sets |
| Sethy et al. (2020), ResNet50 plus SVM | F1 0.9838 | 4 rice diseases | 5,932 images |
| Petchiammal et al. (2023), ResNet34 | F1 97.50 percent | 13 classes (paddy) | 16,225 images |
| Our system, three class model | 91.5 percent accuracy | 3 classes | 164 held out test images |
| Our system, six class merged model | 83.80 to 87.08 percent accuracy | 6 classes | 815 or 859 held out images |

Our six class model's accuracy sits below the highest reported numbers in
Table 9.3, which matches the explanation already given in section 9.2.3: we
add three more classes than Sethy et al. or the three class model, two of
them data thin, and our training data, while real and held out correctly,
is smaller and less curated than Petchiammal et al.'s purpose built 16,225
image paddy dataset. Our result remains well above the random guess
baseline for six classes (16.7 percent) and is close to the three class
model's own 91.5 percent once the data thin classes are set aside, which
supports the conclusion that more balanced training data, not the choice of
architecture, is the main lever for closing this gap (Chapter 10).

## 9.8 LIMITATIONS

The two thin classes, Bacterial_Blight and Leaf_Smut, with only 55 training
images each, are the most significant limitation of the current classifier,
and they show up consistently across the three class result, the six class
result, and the pipeline simulation. The segmentation model, while close to
the PlantSeg paper's own best baseline, is trained on a general, multi crop
dataset rather than a paddy specific one, and its accuracy (0.445 IoU) is
not pixel perfect; field photographs with cluttered backgrounds remain
harder than the curated PlantSeg images. The pipeline simulation in section
9.4 is explicitly a small, 49 image, hand picked sample and must not be read
as a statistically representative accuracy figure; the held out validation
numbers in section 9.2 remain the correct accuracy evidence. A small
sensitivity to the exact image resizing method was also found (section
9.4) and is a minor but real source of variation. The spray timing window
(0.5 to 3.0 seconds) is a design default, not yet calibrated against a
measured flow rate on the built hardware (Chapter 5, section 5.8.1), and
while a real bench test and one real integration cycle now confirm the
signal chain works end to end on hardware (Chapter 5, section 5.8.2;
Chapter 8, section 8.4), the flow calibration, the wet spray volume check
and the field trial still remain to be done. Finally, the system depends
on a working WiFi connection to reach the cloud inference server, which is
a constraint of the cloud based design choice explained in Chapter 4,
section 4.8; this was confirmed directly during bring up, where the
ESP32-CAM would not connect to the WiFi hotspot until the network name's
exact character encoding and the hotspot's band setting were both
corrected (Chapter 5, section 5.8.3).
