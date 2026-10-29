# SCHEDULE, TASKS AND MILESTONES

## 7.1 OVERVIEW

The project was planned and tracked across the semester using the fourteen
week plan presented at Review 2 and carried through to the final review.
Figure 7.1 shows the schedule as a Gantt chart, and Table 7.1 lists the main
tasks, owners and deliverables. The week numbers below are taken from the
Review 2 deck and the hardware plan rather than from a day by day log, and
the hardware related weeks (9 to 12) are ahead of the actual build, which
had not started at the time of writing this report (Chapter 5, section
5.11); the team should confirm the exact calendar dates and note here if
any task slipped from this plan once the physical build is under way.

{{FIG:gantt|figures/fig_gantt.png|Project Gantt chart across the fourteen week plan.}}

## 7.2 TASK TABLE

{{TABLE:schedule_tasks|Task table with owners and deliverables.}}
| Week | Task | Owner | Deliverable |
|---|---|---|---|
| 1 to 2 | Literature review, problem definition, Review 1 | Both | Report chapters 1 and 2 |
| 3 to 4 | CNN classifier training and validation | Sourish Das | Trained classifier above 90 percent on the initial test set |
| 5 to 6 | Flask inference API and ngrok tunnel; Review 2 preparation | Sourish Das | Working cloud API |
| 7 to 8 | ESP32-CAM firmware, image capture and HTTP client | Aditya Singh | ESP32-CAM sends and receives from the API |
| 9 to 10 | Arduino Nano firmware and hardware assembly; Review 3 | Aditya Singh | Valve control working on the bench |
| 11 to 12 | Blynk IoT dashboard, field testing, VRA vs CRA comparison | Both | End to end prototype |
| 13 | Results analysis and report writing; Review 4 | Both | Complete draft report and demo |
| 14 | Final demonstration and viva; Review 5 | Both | Final presentation and submitted report |

## 7.3 MEMBER RESPONSIBILITIES

{{TABLE:member_responsibilities|Primary responsibilities by team member.}}
| Member | Primary responsibilities |
|---|---|
| Sourish Das (23BCE1179) | Classifier and segmentation model development, Flask API development, cloud deployment, Blynk IoT coding |
| Aditya Singh (23BCE1293) | ESP32-CAM firmware development, Arduino Nano control logic, hardware assembly, circuit wiring, system testing |

## 7.4 MILESTONES ACHIEVED

The classifier and the segmentation model were trained, evaluated and
deployed, and are shown working through a live Flask API and the
PaddyGuard web demo (Chapter 6, Chapter 9). A full software simulation of
the decision pipeline was run on 49 real test images, exercising the
classifier, the severity module and the dosing equations together
end to end (Chapter 9). Automated unit tests (37 cases) and API integration
tests (13 cases) were written and run against the real code, with all
cases passing (Chapter 8). The hardware design, bill of materials, wiring
and firmware behaviour were fully specified (Chapter 5); the physical build,
calibration and field trial results depend on the hardware evidence
supplied by the team and are reported in Chapter 5 and Chapter 9 exactly as
available, with placeholders where a reading was not yet supplied at the
time of writing.
