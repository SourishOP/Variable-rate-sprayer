# INTRODUCTION

## 1.1 BACKGROUND

Rice is one of the most important food crops grown in India and in many other
parts of Asia. Farmers who grow paddy depend on a healthy crop for their
income and for their family's food. A paddy field is, however, open to many
diseases caused by bacteria and fungi. Bacterial blight, brown spot, leaf smut
and blast (including the neck blast form that attacks the stem near the ear)
are common examples. Even a partial attack by one of these diseases on a field
can lower the grain yield by a noticeable margin, and a bad outbreak can
destroy a large part of the standing crop. Farmers therefore spray chemical
pesticides and fungicides on their fields to protect the plants.

Most small and medium farms in India still use hand-operated or simple motor
driven sprayers. These sprayers release the chemical at one fixed rate as the
operator walks or drives through the field. The rate does not change with how
sick or how healthy a particular plant is. A plant that shows no disease at
all receives the same dose as a plant with a serious infection. This way of
spraying is called constant rate application (CRA).

## 1.2 THE PROBLEM WITH UNIFORM SPRAYING

Uniform, constant rate spraying wastes chemical on plants that do not need it.
The extra chemical adds to the farmer's cost without adding any benefit, and
it runs off into the soil and nearby water bodies. Heavy and repeated use of
the same chemical also helps pests and pathogens build resistance over time,
which makes the chemical less useful in future seasons. Workers who spray the
field by hand are exposed to more chemical than is needed, and some residue
can remain on the harvested grain.

An alternative is variable rate application (VRA). In VRA, the sprayer senses
how diseased a plant or a zone of the field is, and it adjusts the amount of
chemical released for that plant or zone. A healthy plant gets little or no
chemical, and a badly diseased plant gets a full dose. VRA can therefore cut
the total chemical used while still treating the diseased parts of the field
properly.

VRA systems that use maps made in advance (map based VRA) are not well suited
to disease control, because a disease spreads through a field quickly and a
map made even a day earlier may no longer match the real situation. A
sensor based VRA, where the camera, the processing and the spraying all
happen together in the same pass through the field, is better suited to
disease control because the decision is made from the plant in front of the
nozzle at that moment.

## 1.3 CHEMICAL OVERUSE AND ITS WIDER EFFECT

Chemical overuse in agriculture is a cost problem for the individual farmer,
and it is also an environmental and a health problem. Pesticide residue
that enters streams and groundwater affects aquatic life and can reach
drinking water supplies. Farm workers who handle and apply chemicals without
proper protection face health risks from repeated exposure. Consumers are
also exposed to any residue left on the food they eat. A system that only
sprays what is needed, and only where it is needed, reduces all three of
these effects at the same time, alongside the direct saving in chemical cost.

## 1.4 MOTIVATION

Tewari et al. (2020) built and field tested a variable rate sprayer for paddy
disease control. Their system used two webcams, a laptop running MATLAB, and
a chromatic aberration based image threshold to find diseased leaf regions.
The laptop then worked out a severity level and opened a solenoid valve for a
set time so that the correct volume of chemical was sprayed. Their field
trial, conducted on a 300 square metre paddy plot, showed a minimum chemical
saving of 33.88 percent compared with constant rate spraying. This result
proves that disease severity based variable rate spraying genuinely saves
chemical in a real paddy field, and it is the base paper for our project.

The base paper's own method has limits that later work, including ours, tries
to improve on. A chromatic aberration threshold is a simple colour rule, and
it works less well when the lighting in the field changes, or when a disease
other than the ones it was tuned for appears. A laptop with MATLAB is heavy,
needs mains or a large battery, and is not something a small farmer would want
to carry across a field. The base paper's three severity levels always spray
at least 33 percent of the recommended rate, so even a perfectly healthy plant
receives some chemical.

Convolutional neural networks (CNN) have by now been shown repeatedly to
classify leaf diseases from a photograph more accurately and more robustly
than a hand tuned colour rule, across lighting conditions and across more
disease classes (Mohanty et al., 2016). Small, low power microcontroller
boards with a built in camera and WiFi, such as the ESP32-CAM, together with
free cloud services for running a trained model, now make it possible to
replace the laptop with a device that fits in one hand and costs a fraction of
the price. An internet of things (IoT) dashboard lets a farmer check the
status of the sprayer and the chemical used from a phone, without standing
next to the machine.

These three ideas, a CNN classifier in place of a colour threshold, a compact
ESP32 based controller in place of a laptop, and an added severity level for a
fully healthy plant that receives no spray at all, form the motivation for
this project.

## 1.5 PROBLEM STATEMENT

Existing uniform sprayers waste chemical on healthy plants and under treat
severely diseased plants in the same pass. Existing variable rate systems
that do use image based disease detection, including the base paper, rely on
simple threshold rules that are sensitive to lighting and that generalise
poorly to diseases they were not tuned for, and they run on bulky, costly
compute hardware with no remote monitoring. There is a need for a compact,
low cost system that can classify the specific disease on a paddy leaf,
measure how much of the leaf area it covers, and use both pieces of
information together to decide how much chemical to spray, while also letting
the farmer monitor the process remotely.

## 1.6 OBJECTIVES

The objectives of this project are as follows.

1. Build a deep learning classifier that identifies the disease on a paddy
   leaf image, trained using transfer learning so that it works well with a
   limited amount of labelled rice disease data.
2. Build a severity measurement step that segments the diseased pixels on the
   leaf and reports the diseased area as a percentage of the leaf area,
   instead of relying on the classifier's confidence score as a proxy for
   severity.
3. Combine the disease class and the measured severity into a reduction
   coefficient, and from the coefficient compute the chemical volume per
   plant and the solenoid valve open time needed to deliver that volume.
4. Design a compact, low cost hardware path, an ESP32-CAM for image capture
   and WiFi, an Arduino Nano for valve timing, a relay driven solenoid valve
   and a small pump, that carries out the spray decision in the field.
5. Provide an IoT dashboard so that severity readings, chemical usage and
   alerts can be checked remotely, and provide a web demonstration interface
   that shows the full decision process on an uploaded leaf photograph.
6. Measure the system's classification accuracy, severity measurement
   quality and the chemical saving against constant rate spraying, and
   compare these results with the base paper and with other published work.

## 1.7 SCOPE OF THE PROJECT

The project covers the paddy crop and six leaf conditions: a healthy leaf and
five disease classes, bacterial blight, brown spot, leaf smut, blast and neck
blast. The classification model and the severity pipeline are built, trained
and tested in software, and are demonstrated through a Flask based web
application. The spray decision logic (severity to coefficient to chemical
volume to valve open time) is implemented in the same software and is also
the logic that the hardware firmware is designed to follow. Cloud based
inference is used, through a Flask server that the ESP32-CAM reaches over
WiFi, because running a CNN directly on a microcontroller is outside the
budget and time available for this project; on device inference with a
smaller, converted model is noted as future work in Chapter 10. The hardware
build follows the bill of materials and wiring plan described in Chapter 5;
any measured bench, integration or field results depend on the physical
prototype build reported by the team, and are presented exactly as supplied,
with a clearly marked placeholder wherever a reading was not yet available at
the time of writing this report.
