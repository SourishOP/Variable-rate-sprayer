# LITERATURE SURVEY AND PROJECT GOALS

## 2.1 OVERVIEW

This chapter reviews published work in three areas that are relevant to our
project: variable rate spraying systems, deep learning for plant disease
detection, and sensing or monitoring methods used in precision agriculture.
Each paper is summarised in terms of what it did, what it found, and what it
does not cover. The chapter ends with the research gap we identified and the
way our project addresses that gap.

## 2.2 VARIABLE RATE SPRAYING SYSTEMS

Tewari et al. (2020) is the base paper for this project. The authors built a
prototype that used two webcams and a laptop running MATLAB to capture images
of paddy plants, a chromatic aberration based threshold to find the diseased
leaf region, and an Arduino microcontroller to open a solenoid valve for a
computed duration. Three severity levels (low, medium, high, covering 0 to 5
percent, 5.1 to 20 percent and above 20 percent diseased area) were each
assigned a fixed reduction coefficient of 0.33, 0.67 and 1.00 of the
recommended chemical rate. Field testing in a 300 square metre paddy plot
with 20 by 20 centimetre hill spacing, using the fungicide monocrotophos 36SL,
gave an average constant rate application (CRA) volume of 504.17 L/ha and an
average variable rate application (VRA) volume of 319.5 L/ha, a minimum
chemical saving of 33.88 percent (reduction varied between 33.88 and 40.47
percent across trials, with an average reduction of 36.65 percent, found
significant at p less than or equal to 0.05). The method is sensitive to
lighting because chromatic aberration thresholding is a colour based rule,
it needs a laptop in the field, and it always sprays at least 33 percent of
the recommended dose even on a plant with almost no disease.

Oberti et al. (2016) built a modular agricultural robot under the EU CROPS
project that carried an R-G-NIR multispectral disease sensor and a precision
spraying end effector to control powdery mildew on grapevines. Their robot
detected 85 to 100 percent of the diseased canopy area and reduced pesticide
use by 65 to 85 percent compared with uniform spraying. The system is complex
and costly to build, and it is tuned specifically to grapevine canopies and a
single disease, which limits how directly it can be reused for a paddy crop.

Esau et al. (2013) developed an automated, prototype variable rate sprayer
for wild blueberry that used machine vision to tell foliage apart from bare
soil, and sprayed fungicide only on the foliage. Measured fungicide saving
ranged from 9.90 to 51.22 percent depending on the field's bare spot pattern.
Their decision is a binary spray or no spray choice based on foliage
presence; it does not estimate how diseased the foliage actually is, so it
cannot scale the dose to disease severity the way our project does.

Zhang et al. (2025) proposed a variable rate sprayer for fruit trees that
fuses two sensing modes, a canopy volume measurement (4.34 percent error) and
a disease spot detector (82.6 percent accuracy), to set the spray dose. Their
system reduced chemical use by 74.0 percent at low disease severity and by
42.7 percent at high severity compared with a conventional sprayer, and a
field trial on pear rust reached 86.53 percent disease control with 66.4 and
22.2 percent savings against a traditional sprayer and a volume only variable
rate sprayer respectively. Their canopy volume sensor is built for tree
shaped crops and is not suited to a low growing crop such as paddy, which has
little canopy depth to measure.

Abioye et al. (2024) presented a small robotic sprayer for a citrus nursery
that used a MobileNetV2 model on a Raspberry Pi 4 to classify plant samples
with a reported classification accuracy of 100 percent on their controlled,
indoor test set, and reached 87 percent spray coverage on lemon foliage
against 67 percent on navel orange, measured with water sensitive cards. The
robot works indoors on potted nursery plants and does not report a severity
based dosage; it sprays by classification result alone.

Samseemoung et al. (2017) designed a variable rate sprayer for coconut
plantations that used classical image processing to estimate disease density
and wireless remote monitoring to track the spraying operation. They found
optimal design values of 1 metre nozzle to target distance, 1.5 bar pressure,
2.712 L/min spray rate, 1.5 km/h movement speed, 0.58 L/h fuel use and 0.056
ha/h working capacity for a tree sized crop. The system does not use deep
learning and is specific to tall, widely spaced trees, unlike the dense,
low growing paddy rows this project targets.

## 2.3 WEED DETECTION AND SITE SPECIFIC SPRAYING

Xu et al. (2018) built a real time weed mapping and precision herbicide
spraying system for row crops that used an improved particle swarm
optimisation (IPSO) algorithm to segment weeds from crop, cutting the
segmentation error rate from 7.1 to 0.1 percent with a processing speed of
0.026 seconds per frame, and a measured weed detection to spray actuation
response time of 1.562 seconds. This is a useful reference point for how
fast a sensor based variable rate system needs to respond, but the paper
targets weeds, not crop disease, and it does not estimate a severity level.

Partel et al. (2019) developed a low cost smart sprayer using a custom CNN
for real time weed detection paired with individually actuated nozzles.
Using the stronger of their two embedded GPUs, they reached 71 percent
precision and 78 percent recall on a scenario with real plants, and 91
percent accuracy on an easier scenario with artificial plants. Their system
is weed focused and makes a simple target or non target decision rather than
grading a severity level.

Rehman et al. (2019) built a machine vision weed detector for wild blueberry
fields using colour co-occurrence texture features and a quadratic
classifier, reaching 94.98 percent training accuracy and 93.80 percent test
accuracy in laboratory evaluation, and field savings between 30.12 and 60.58
percent depending on the amount of weed cover. Their method relies on
hand engineered texture features rather than a learned deep network, and
again addresses weeds rather than plant disease.

## 2.4 DEEP LEARNING FOR PLANT AND RICE DISEASE DETECTION

Mohanty et al. (2016) trained AlexNet and GoogLeNet with transfer learning on
54,306 images covering 14 crop species and 26 diseases from the PlantVillage
dataset, reaching 99.35 percent accuracy with GoogLeNet and colour images on
a held out test set drawn from the same distribution as the training images.
When the same trained model was tested on two independent sets of images
taken under uncontrolled field conditions, accuracy fell sharply to 31.40 and
31.69 percent (a random guess baseline would score 2.63 percent). This
lab to field accuracy gap is an important lesson for our project: a
classifier that scores well on a clean, single leaf benchmark image can
still perform far worse on a messy, real world photograph, and our own
pipeline simulation (Chapter 9) shows a version of the same effect on a small
hand picked test set.

Sethy et al. (2020) compared 11 CNN backbones used as transfer learned
classifiers against the same backbones used only as deep feature extractors
followed by a support vector machine (SVM), on 5,932 field images of four
rice diseases (bacterial blight, blast, brown spot and tungro). The best
result was ResNet50 features combined with an SVM, with an F1 score of
0.9838; a lightweight MobileNetV2 plus SVM combination reached a comparable
F1 score of 0.9796. Their best setup needs a separate SVM training stage
after the CNN feature extraction step, which adds complexity compared with
an end to end classifier such as the one used in our project.

Rahman et al. (2020) trained a custom, two stage small CNN on 1,426 rice
images covering 9 diseases and 3 pest categories, comparing it with
MobileNet, NASNet-Mobile and SqueezeNet. Their proposed small model reached
93.3 percent accuracy with a model size about 99 percent smaller than VGG16,
which is a useful demonstration that a small CNN can match larger backbones
on a rice disease task, but their dataset and classes do not match our six
paddy classes directly.

Petchiammal et al. (2023) released the Paddy Doctor dataset, 16,225 labelled
paddy leaf images across 13 classes (12 diseases and a healthy class), and
benchmarked it with ResNet34, VGG16, MobileNet and Xception. ResNet34 gave
the best result, an F1 score of 97.50 percent. This dataset is one of the
larger public paddy specific resources available, and its scale is a useful
comparison point for the size of our own merged training set (Chapter 4).

Chen et al. (2020) used InceptionV3 with ImageNet transfer learning plus a
domain adaptation step to narrow the gap between laboratory and field
conditions, reaching at least 91.83 percent validation accuracy on a public
dataset and 92.00 percent average accuracy on real rice field images. Their
domain adaptation idea, training with both clean and field like images so
the model generalises better to the field, is a relevant direction for
improving our own classifier's field performance in future work.

PlantSeg (Wei et al., 2024) is a large, in the wild dataset built for plant
disease segmentation rather than classification, containing 11,400 diseased
images and 8,000 healthy images with pixel level masks across many crop
species and disease categories. The paper's own strongest baseline model,
SegNeXt with an MSCAN-L backbone, reached 44.52 percent mean intersection
over union (mIoU) and 59.95 percent mean pixel accuracy (mAcc) on their test
split; lighter baselines such as DeepLabV3 and DeepLabV3+ reached only 17 to
27 percent mIoU. We use PlantSeg to train our own lesion segmentation model
(Chapter 4), and our measured validation performance is compared against
these baseline numbers in Chapter 9.

## 2.5 RESEARCH GAP

Putting the above work together, three gaps stand out for a paddy specific,
low cost, severity based sprayer.

First, the systems that actually spray variable amounts in the field
(Tewari et al., Oberti et al., Esau et al., Zhang et al., Samseemoung et al.)
either use simple colour or texture thresholds instead of a learned deep
network, or they run on costly, bulky compute hardware such as a laptop with
MATLAB or a full sized robot platform. None of them pair a CNN disease
classifier with a separately measured, pixel level severity score and a
compact, WiFi connected microcontroller.

Second, the systems that do use strong CNN classifiers for plant disease
(Mohanty et al., Sethy et al., Rahman et al., Petchiammal et al., Chen et
al.) are evaluated purely as classification benchmarks. They report accuracy
on a labelled test set but do not connect their output to an actual spray
dose or valve timing, and they do not report a measured severity percentage
derived from segmentation.

Third, the base paper's three severity levels always spray a minimum of 33
percent of the recommended rate, so a plant with no visible disease at all
still receives chemical. No paper in this survey adds an explicit, zero
chemical "Healthy" category driven by the classifier, which is a direct,
simple way to remove wasted spraying on healthy plants.

## 2.6 PROBLEM STATEMENT (RESTATED FOR DESIGN)

Based on the gap above, the specific problem this project solves is: how to
combine a CNN disease classifier and a pixel level severity measurement, on
compact and low cost hardware with remote monitoring, so that a paddy
sprayer can apply the correct chemical dose for each plant, including zero
dose for a healthy plant, without depending on a laptop or a hand tuned
colour threshold.

## 2.7 OBJECTIVES AND NOVELTY OVER THE BASE PAPER

Table 2.1 summarises how our system differs from the base paper, Tewari et
al. (2020), on each of the main design points.

{{TABLE:novelty_vs_base|Comparison of the base paper and our proposed system.}}
| Aspect | Tewari et al. (2020), base paper | Our system |
|---|---|---|
| Disease detection | Chromatic aberration colour threshold | EfficientNetV2-B0 CNN classifier, transfer learning |
| Severity measurement | Same colour threshold used for both detection and severity | Separate U-Net segmentation model measures diseased pixels |
| Compute platform | Laptop with MATLAB | ESP32-CAM plus cloud Flask inference |
| Monitoring | None | Blynk IoT dashboard and a web demo interface |
| Severity levels | 3 levels, minimum spray is 33 percent of recommended rate | 4 levels, Healthy class sprays 0 percent |
| Dose scaling | Same coefficient for every disease at a given severity | Per disease factor further scales the coefficient |
| Estimated cost | Laptop, webcams and a MATLAB licence | Target under Rs. 2,500 (Chapter 5) |

Our specific contributions, in line with the objectives in Chapter 1, are:
replacing the colour threshold with a trained CNN classifier so that
detection is more robust to lighting and covers more disease classes;
measuring severity with its own segmentation model rather than reusing the
classifier's confidence score, so the severity number reflects the actual
diseased leaf area; adding a per disease dosing factor, because some
diseases, such as neck blast, are treated as needing a relatively higher
dose at the same severity level than others; and replacing the laptop with a
compact ESP32-CAM and Arduino Nano pair, with a Blynk dashboard for remote
status. These points are described in full in Chapters 4, 5 and 6, and are
checked against measured results in Chapter 9.
