# CONCLUSION AND FUTURE WORK

## 10.1 SUMMARY OF WHAT WAS BUILT

This project set out to replace the base paper's laptop and colour threshold
based variable rate sprayer (Tewari et al., 2020) with a compact, deep
learning based system for paddy disease control. We built and trained a
six class EfficientNetV2-B0 disease classifier, a U-Net lesion segmentation
model that measures severity directly from diseased pixels rather than from
classifier confidence, a severity to dose and spray time calculation module,
a Flask inference API, a web demonstration interface (PaddyGuard), and a
hardware design built around an ESP32-CAM and an Arduino Nano with a Blynk
dashboard for remote monitoring. All of the software components were
implemented, tested and are shown running on real data: 37 unit tests and 13
API integration tests passed, and a full pipeline simulation was run on 49
real leaf images from the project's own test set.

## 10.2 WHAT WORKED WELL

The classifier reached 91.5 percent accuracy on a held out, three class test
set, and 83.80 to 87.08 percent on the harder, six class merged dataset, with
the Neck_Blast class classified perfectly in both the larger validation runs
and the smaller pipeline simulation. The severity module's category
thresholds, disease factors, severity floor and confidence gate all behaved
exactly as designed across every unit test case. The lesion segmentation
model reached a mean IoU of 0.445 on the PlantSeg validation set, close to
that dataset's own strongest published baseline, using a much smaller
encoder. The complete pipeline, from an uploaded leaf image through to a
computed spray time, runs correctly end to end, and the API responds inside
one second once warmed up, which supports the project's real time design
goal. The simulated chemical saving, 40 to 43 percent against a constant
full rate baseline, is higher than the base paper's own field measured
33.88 percent minimum saving, consistent with the added Healthy, zero spray
category that the base paper's three level system does not have.

## 10.3 WHAT DID NOT FULLY SUCCEED

Two of the six disease classes, Bacterial_Blight and Leaf_Smut, have only 55
training images each, and this shows up as weaker, less reliable
predictions for those two classes throughout the results in Chapter 9. The
six class model's overall accuracy, while reasonable, is below the near
99 percent figures reported by some related work (Chapter 2, Chapter 9),
because those studies either used far larger, purpose built datasets or
fewer classes. The pipeline simulation on 49 real images showed that the
severity floor and confidence gate guards, while correct by design, can
lower the apparent accuracy on a small, uneven sample; this is an honest,
explainable result rather than a hidden failure, but it means the system's
behaviour on a small set of field photographs should not be judged by that
one number alone. At the time of writing this report, the physical ESP32-CAM
and Arduino Nano have been flashed, bench tested on their own, and run
through one real pairwise integration cycle (Chapter 5, section 5.8.2),
which confirms the full signal chain works end to end on real hardware,
but the flow rate calibration, the spray volume check with water, the full
battery powered run, and the field trial comparing constant rate and
variable rate chemical use had not yet been done, so these specific
hardware measured results still rely on placeholders rather than completed
measurements; this gap is listed in full in OPEN_ITEMS.md and is the
largest piece of unfinished work remaining on the project as a whole.

## 10.4 COMPARISON WITH THE PLANNED TARGETS

The project proposal (Chapter 2, Chapter 3) set a classification accuracy
target of above 90 percent, a chemical saving target of at least 33
percent, a budget target under Rs. 2,500, and a spray cycle target under 5
seconds. The classifier met the 90 percent target on the three class model
(91.5 percent) but fell short of it on the harder six class model (83.80 to
87.08 percent), for the data thin class reasons already discussed. The
simulated chemical saving, 40 to 43 percent, met and exceeded the 33 percent
target, though this is a software simulation rather than the field
measurement the target was originally framed against. The hardware bill of
materials stays within the Rs. 2,500 budget target on paper (Chapter 5); the
actual amount spent by the team has not yet been confirmed against this
report. The 5 second spray cycle target depends on hardware actuation and
network timing; the one real integration cycle recorded in Chapter 5,
section 5.8.2 shows the complete chain running, but a proper timed
measurement over at least ten runs, as planned in Chapter 5, section 5.8
and Chapter 8, section 8.4, remains to be done before this target can be
confirmed with real cycle time numbers.

## 10.5 OWN CONTRIBUTION VERSUS EXISTING WORK

The core dose and spray time equations, `a = (C x A) / (d x 10)` and the
idea of mapping severity to a reduction coefficient in discrete bands, are
taken directly from the base paper, Tewari et al. (2020), and are credited
to it throughout this report. Our own contribution is replacing the base
paper's chromatic aberration colour threshold with a trained CNN classifier
and a separately trained pixel level segmentation model; adding a fourth,
zero spray Healthy category and a per disease dosing factor, neither of
which appears in the base paper's three level system; replacing the laptop
and MATLAB compute platform with a compact ESP32-CAM and Arduino Nano pair
reached over cloud inference; and adding a Blynk based remote dashboard and
a browser based demonstration interface, PaddyGuard, which shows the full
decision process on a single uploaded image. None of the literature
reviewed in Chapter 2 combines a trained CNN classifier, a separately
measured segmentation based severity score, and a compact, remotely
monitored microcontroller platform in the way this project does; this
combination, not any single piece of it on its own, is the project's main
contribution.

## 10.6 INSIGHTS GAINED

Working through this project surfaced a few insights that were not obvious
at the start. First, a classifier's accuracy on a clean, well balanced test
set can hide weak performance on classes with little training data; our
project's own 55 image classes made this very concrete rather than
abstract. Second, guard logic meant to make a system safer, such as our
severity floor and confidence gate, can lower a simple accuracy number on a
small or unusual sample even while making the system behave more sensibly
overall; a results chapter has to explain this clearly rather than treat a
lower number as automatically bad. Third, keeping the reporting honest
about what is measured versus what is calculated, our simulated 40 to 43
percent chemical saving versus the base paper's field measured 33.88
percent, for example, matters more than it might first seem, because the
two kinds of evidence are not interchangeable even when the numbers look
comparable.

## 10.7 FUTURE WORK

Collecting more training images for the two thin classes, Bacterial_Blight
and Leaf_Smut, is the single biggest likely improvement to classification
accuracy, and should be the first priority if the project continues. Using
a higher input resolution (299 or 384 pixels instead of the current input
size) and a larger EfficientNetV2 variant (B2 or B3) may help separate the
visually similar Blast and Brown_Spot classes, at some cost to inference
speed that would need to be re measured against the real time budget.
Converting the trained models to TensorFlow Lite and running them directly
on an edge device, such as a Raspberry Pi or the ESP32 itself, would remove
the project's dependence on a WiFi connection to a cloud server, at the cost
of either a smaller model or slower on device inference, and is a natural
next step once the cloud based version is fully proven in the field.
Completing the hardware calibration, measuring the real pump and solenoid
flow rate and re tuning the spray time equation against it, is necessary
before any hardware measured result in this report can be treated as final,
and the field trial comparing constant rate and variable rate chemical use
on a real paddy row should be carried out and reported once the hardware
build is complete, to give a true field measured chemical saving figure
that can be compared directly with the base paper's 33.88 percent.
