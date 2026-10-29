# TECHNICAL SPECIFICATION

## 3.1 OVERVIEW

This chapter lists what the system must do (functional requirements), what
quality it must meet while doing it (non functional requirements), and
whether the project is realistic to build within the available time, budget
and skills (feasibility). It also lists the hardware and software
specification used in the rest of the report.

## 3.2 FUNCTIONAL REQUIREMENTS

{{TABLE:functional_requirements|Functional requirements of the system.}}
| ID | Requirement |
|---|---|
| FR1 | The system shall accept a paddy leaf image, either uploaded through the web demo or captured by the ESP32-CAM. |
| FR2 | The system shall classify the leaf image into one of six classes: Healthy, Bacterial_Blight, Blast, Brown_Spot, Leaf_Smut, Neck_Blast. |
| FR3 | The system shall segment the leaf into leaf pixels and diseased pixels and report severity as a percentage of leaf area. |
| FR4 | The system shall map severity percentage to one of four categories (Healthy, Low, Medium, High) using fixed thresholds, each with a base reduction coefficient. |
| FR5 | The system shall scale the base coefficient by a disease specific factor to get an effective reduction coefficient. |
| FR6 | The system shall compute the chemical dose per hill and the solenoid valve open time from the effective coefficient, using the stated dose equations. |
| FR7 | The system shall flag a prediction as low confidence when the classifier's top score is below a fixed threshold. |
| FR8 | The system shall treat a severity reading below a fixed floor as Healthy, even if the classifier predicted a disease, to avoid spraying for a few stray pixels. |
| FR9 | The hardware shall receive the category from the cloud inference step over WiFi and actuate the solenoid valve for the computed duration. |
| FR10 | The system shall report status, severity and chemical usage on a remote IoT dashboard (Blynk). |
| FR11 | The web demo shall show the uploaded leaf, the predicted class and confidence, the segmented mask, the severity calculation steps, and the resulting valve open time, for the panel and for general use. |

## 3.3 NON FUNCTIONAL REQUIREMENTS

{{TABLE:non_functional_requirements|Non functional requirements of the system.}}
| ID | Requirement |
|---|---|
| NFR1 | Classification accuracy on a held out validation set should be above 80 percent for the deployed six class model. |
| NFR2 | One full inference cycle (classification plus severity) should typically complete in under one second on the cloud server, excluding network transfer time. |
| NFR3 | The complete spray decision cycle, from image capture to valve actuation, should stay under 5 seconds under normal WiFi conditions. |
| NFR4 | The hardware bill of materials should stay close to the Rs. 2,500 budget target set at the proposal stage. |
| NFR5 | The system should degrade gracefully: if the trained segmentation model is not available, a classical colour based severity method should still run; if automatic leaf isolation fails, the user should be able to trace the leaf outline by hand. |
| NFR6 | The valve open time should always stay within a safe window (0.5 to 3.0 seconds) so a wrong reading cannot empty the tank in one cycle. |
| NFR7 | The web demo and the API should be usable without installing anything beyond a web browser on the client side. |

## 3.4 FEASIBILITY STUDY

### 3.4.1 Technical feasibility

The project uses well tested, publicly documented building blocks:
EfficientNetV2-B0 and U-Net are standard, well published architectures;
TensorFlow and Keras are mature, free libraries with large community support;
the ESP32-CAM, Arduino Nano, relay module and solenoid valve are commodity
parts that are commonly used together in hobbyist and small scale automation
projects; Flask is a lightweight, well known Python web framework suited to
exposing a trained model as an HTTP endpoint; and Blynk provides a free tier
IoT dashboard with ready made mobile and web clients. All of the software
components were implemented and tested during this project (Chapters 6, 8
and 9), which confirms they work together as planned. The main technical
risk, keeping cloud inference fast enough for a 5 second spray cycle, was
measured directly (Chapter 8, API test results) rather than assumed.

### 3.4.2 Economic feasibility

The complete hardware bill of materials (Chapter 5) targets a build cost of
around Rs. 2,250 to Rs. 2,400, with a full possible range of Rs. 1,930 to Rs.
2,720 depending on the exact parts sourced. All of the software tools used
(TensorFlow, Flask, the Arduino IDE, Google Colab's free GPU tier, and
Blynk's free tier) are free to use. This keeps the total cost of the
prototype low enough to be realistic for a student project and, longer term,
for a smallholder farmer, which was one of the motivations in Chapter 1.

### 3.4.3 Social feasibility

A system that reduces chemical cost and chemical exposure benefits the
farmer directly, and reducing pesticide runoff benefits the wider community
and environment around the field, as discussed in Chapter 1. The hardware
and firmware are deliberately kept simple (an Arduino Nano, a single relay,
one solenoid valve) so that a farmer or a local technician without
specialised training could realistically maintain the prototype, which
matters for the system to be socially useful rather than only being usable
inside a lab.

## 3.5 HARDWARE SPECIFICATION

{{TABLE:hardware_spec|Hardware specification summary (full bill of materials in Chapter 5).}}
| Component | Specification |
|---|---|
| Image capture and WiFi | AI-Thinker ESP32-CAM, OV2640 type sensor, 320 by 240 pixel raw RGB565 capture (the fitted camera module has no hardware JPEG, Chapter 5, section 5.6.1), 4 MB PSRAM, 802.11 b/g/n WiFi |
| Valve control microcontroller | Arduino Nano V3.0, ATmega328P, CH340 USB to serial |
| Actuation | 5 V, 1 channel relay module with optocoupler isolation |
| Flow control | 12 V DC, normally closed, 1/2 inch solenoid valve |
| Liquid delivery | R385 12 V DC diaphragm pump, self priming, about 1.5 to 2 L/min |
| Spray pattern | Adjustable brass hollow cone nozzle, 1/4 inch thread |
| Power source | 3 x 18650 Li-ion cells (about 11.1 V nominal) or a 12 V sealed lead acid battery |
| Voltage regulation | LM2596 adjustable buck converter, set to 5.00 V for the microcontrollers and relay |
| Liquid path | 6 mm internal diameter food grade silicone tubing |

## 3.6 SOFTWARE SPECIFICATION

{{TABLE:software_spec|Software specification summary.}}
| Layer | Technology | Purpose |
|---|---|---|
| Model training | Python, TensorFlow and Keras, Google Colab (GPU) | Train the classifier and the segmentation model |
| Disease classifier | EfficientNetV2-B0, transfer learning | Classify the leaf image into one of six classes |
| Lesion segmenter | U-Net with a MobileNetV2 encoder, Dice plus binary cross entropy loss | Segment diseased pixels from leaf pixels |
| Interactive leaf isolation | MobileSAM, plus a free form polygon fallback | Isolate the leaf from a cluttered background when needed |
| Inference API | Flask, running the trained models | Serves the `/predict` endpoint used by the web demo and by the ESP32-CAM |
| Web demo | HTML, CSS and JavaScript (static page served by Flask) | Lets a user upload a leaf photo and see the full decision process |
| ESP32-CAM firmware | Arduino IDE, HTTPClient library | Captures the image, sends it to the API, receives the category, forwards it to the Nano |
| Arduino Nano firmware | Arduino IDE, SoftwareSerial library | Computes the valve open time and drives the relay |
| IoT dashboard | Blynk (free tier) | Remote monitoring of severity, usage and alerts |

## 3.7 ASSUMPTIONS AND CONSTRAINTS

The system assumes a working WiFi connection (a mobile hotspot or a field
router) is available so the ESP32-CAM can reach the cloud inference server;
this is a known constraint of the cloud based design and is discussed again
as a limitation in Chapter 9. The default dosing constants, an application
rate (A) of 500 L/ha and a hill density (d) of 25 hills per square metre, and
the design flow rate (Qs) of 3.5 mL/s, are taken from the hardware plan as
starting values; the flow rate in particular is meant to be replaced by a
measured value once the pump and solenoid are calibrated on the built
prototype (Chapter 5, Chapter 8). The six leaf classes used by the model
(Chapter 4) are the classes the training data provides; other paddy
diseases that are not in the training data are outside the current scope.
