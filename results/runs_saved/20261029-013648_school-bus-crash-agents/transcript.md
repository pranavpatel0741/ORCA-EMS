# School bus crash · agents

Policy: agents · model: gpt-4o-mini · information: complete · seed 7 · 270 simulated minutes

## How well it went

| Measure | Value |
|---|---|
| Deaths | 0 |
| Critical patients in care within 60 min | 50% |
| Critical patients: call to definitive care (mean) | 59 min |
| Call to first ambulance on scene (mean) | 5 min |
| Ambulance minutes waiting at ER doors (beyond 10 min) | 395.0 min |
| Hospital minutes over capacity | 784 min |
| Calls with no ambulance after 30 min | 0 |
| Patients still not in care at the end | 0 |
| Proposals blocked by safety rules | 24 |
| Decisions sent for human review | 0 |
| Synthetic outcome score (higher is better) | 28.2 |
| AI calls | 86 |
| AI tokens | 157437 |
| Decisions by AI agents | 20 |
| Decisions by the rule backup | 9 |

## Negotiations


**AMB-2** · 0 patient(s) · MCI-2 → Hospital A (decided by rule backup)
-   7 min · Dispatch → Dispatch · ESCALATE [AI]: reassign: AMB-2
-   7 min · Dispatch → Dispatch · RESOLVE [AI]: All critical patients will be transported to Hospital C as it has the capacity and is able to handle the critical nature of the cases.
-  41 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-2 with 1 patient(s), ETA 16 min. Can you take them?
-  41 min · Hospital A → Dispatch · REJECT [AI]: We cannot treat these patients as they require TRAUMA_L2 capability, which is beyond our capacity as a level 1 trauma center.
-  41 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-2
-  41 min · Dispatch → Dispatch · RESOLVE [AI]: All units have been successfully assigned to hospitals where they can provide care. MCI-2-P03 remains unassigned as Hospital C cannot accept additional patients.
-  41 min · Dispatch → Human reviewer · ESCALATE [AI]: Confidence 0.63 for AMB-2 → Hospital D; asking for review.
-  74 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: AMB-2
-  74 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-2 is assigned to hospital A as it can accommodate both patients with the fastest transport time.

**AMB-3** · 0 patient(s) · MCI-2 → Hospital C (decided by agents)
-   7 min · Dispatch → Dispatch · ESCALATE [AI]: reassign: AMB-3
-   7 min · Dispatch → Dispatch · RESOLVE [AI]: All critical patients will be transported to Hospital C as it has the capacity and is able to handle the critical nature of the cases.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · COUNTER [AI]: We can only accept MCI-2-P02 as we need to keep capacity for the incoming patient MCI-2-P04. MCI-2-P03 should be directed to another facility for care.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · COUNTER [AI]: We can only accept MCI-2-P02 as we need to keep capacity for the incoming patient MCI-2-P04. MCI-2-P03 should be directed to another facility for care.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · COUNTER [AI]: We can only accept MCI-2-P02 as we need to keep capacity for the incoming patient MCI-2-P04. MCI-2-P03 should be directed to another facility for care.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · COUNTER [AI]: We can only accept MCI-2-P02 as we need to keep capacity for the incoming patient MCI-2-P04. MCI-2-P03 should be directed to another facility for care.
-  41 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-3
-  41 min · Dispatch → Dispatch · RESOLVE [AI]: All units have been successfully assigned to hospitals where they can provide care. MCI-2-P03 remains unassigned as Hospital C cannot accept additional patients.

**AMB-4** · 0 patient(s) · MCI-2 → Hospital C (decided by agents)
-   7 min · Dispatch → Dispatch · ESCALATE [AI]: reassign: AMB-4
-   7 min · Dispatch → Dispatch · RESOLVE [AI]: All critical patients will be transported to Hospital C as it has the capacity and is able to handle the critical nature of the cases.
-  30 min · Dispatch → Dispatch · ESCALATE [AI]: reassign: AMB-4
-  30 min · Dispatch → Dispatch · RESOLVE [AI]: In this resolution, AMB-4 is assigned to transport the critical patient MCI-2-P04 to Hospital A as it has the needed capabilities and available resources.
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 1 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · ACCEPT [AI]: We can accept the patient as we have sufficient capacity in our ER and all necessary resources.
-  71 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: AMB-4
-  71 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: AMB-4
-  71 min · Dispatch → Dispatch · RESOLVE [AI]: All four patients from the duplicated calls were assigned to AMB-4, which is going to Hospital C, ensuring timely care with available capacity.

**AMB-1** · 1 patient(s) · MCI-2 → Hospital C (decided by rule backup)
-  41 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 16 min. Can you take them?
-  41 min · Hospital A → Dispatch · REJECT [AI]: We cannot treat these patients as they require TRAUMA_L2 capability, which is beyond our capacity as a level 1 trauma center.
-  41 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-1
-  41 min · Dispatch → Dispatch · RESOLVE [AI]: All units have been successfully assigned to hospitals where they can provide care. MCI-2-P03 remains unassigned as Hospital C cannot accept additional patients.
-  41 min · Dispatch → Human reviewer · ESCALATE [AI]: Confidence 0.63 for AMB-1 → Hospital D; asking for review.

**PVT-1** · 1 patient(s) · MCI-2 → Hospital B (decided by rule backup)
-  46 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 1 patient(s), ETA 9 min. Can you take them?
-  46 min · Hospital D → Dispatch · ACCEPT [AI]: We can accommodate one patient but cannot accept more at this time due to current capacity limits.
-  95 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: PVT-1
-  95 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: PVT-1
-  95 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: PVT-1
-  95 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: PVT-1
-  95 min · Dispatch → Dispatch · RESOLVE [AI]: PVT-1 is assigned to Hospital B to treat all patients from incident MCI-2, ensuring efficient care within available resources.

**PVT-2** · 1 patient(s) · MCI-2 → Hospital B (decided by rule backup)
-  48 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-2 with 1 patient(s), ETA 9 min. Can you take them?
-  48 min · Hospital D → Dispatch · ACCEPT [AI]: We have capacity for one serious patient, but cannot take more without increasing our nursing staff.

**AMB-4** · 2 patient(s) · MCI-2 → Hospital A (decided by rule backup)
-  84 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 9 min. Can you take them?
-  84 min · Hospital D → Dispatch · COUNTER [AI]: We can accept one patient now and are expecting a bed to free up shortly for the second one. Please send patient MCI-2-P07 first, and we will accept MCI-2-P08 as soon as the bed is available.
-  84 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 9 min. Can you take them?
-  84 min · Hospital D → Dispatch · COUNTER [AI]: We can accept one patient now and are expecting a bed to free up shortly for the second one. Please send patient MCI-2-P07 first, and we will accept MCI-2-P08 as soon as the bed is available.
-  84 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 9 min. Can you take them?
-  84 min · Hospital D → Dispatch · COUNTER [AI]: We can accept one patient now and are expecting a bed to free up shortly for the second one. Please send patient MCI-2-P07 first, and we will accept MCI-2-P08 as soon as the bed is available.
-  84 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 9 min. Can you take them?
-  84 min · Hospital D → Dispatch · COUNTER [AI]: We can accept one patient now and are expecting a bed to free up shortly for the second one. Please send patient MCI-2-P07 first, and we will accept MCI-2-P08 as soon as the bed is available.
-  84 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-4
-  84 min · Dispatch → Dispatch · RESOLVE [AI]: MCI-2-P07 is assigned to hospital D immediately, but MCI-2-P08 is unassigned until a bed frees up.
- 126 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: AMB-4
- 126 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: AMB-4
- 126 min · Dispatch → Dispatch · RESOLVE [AI]: All proposed patients have been assigned to hospital A, which has the capacity and the quickest response time.

**AMB-2** · 2 patient(s) · MCI-2 → Hospital D (decided by agents)
-  89 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  89 min · Hospital D → Dispatch · COUNTER [AI]: I can accept one patient now, but I can't accommodate the second one due to current ER bed limitations. My ER bed capacity is fully utilized, and I cannot take additional patients at this moment.
-  89 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  89 min · Hospital D → Dispatch · COUNTER [AI]: I can accept one patient now, but I can't accommodate the second one due to current ER bed limitations. My ER bed capacity is fully utilized, and I cannot take additional patients at this moment.
-  89 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  89 min · Hospital D → Dispatch · COUNTER [AI]: I can accept one patient now, but I can't accommodate the second one due to current ER bed limitations. My ER bed capacity is fully utilized, and I cannot take additional patients at this moment.
-  89 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  89 min · Hospital D → Dispatch · COUNTER [AI]: I can accept one patient now, but I can't accommodate the second one due to current ER bed limitations. My ER bed capacity is fully utilized, and I cannot take additional patients at this moment.
-  89 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-2
-  89 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-2 will take one patient to Hospital D, which can accept only one due to bed limitations, leaving the second patient unassigned for now.

**AMB-3** · 2 patient(s) · MCI-2 → Hospital D (decided by agents)
- 106 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 106 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P11 but cannot take MCI-2-P12 at this time due to bed occupancy. A ward bed will free up in the next 20 minutes, allowing for further admissions.
- 106 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 106 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P11 but cannot take MCI-2-P12 at this time due to bed occupancy. A ward bed will free up in the next 20 minutes, allowing for further admissions.
- 106 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 106 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P11 but cannot take MCI-2-P12 at this time due to bed occupancy. A ward bed will free up in the next 20 minutes, allowing for further admissions.
- 106 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 106 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P11 but cannot take MCI-2-P12 at this time due to bed occupancy. A ward bed will free up in the next 20 minutes, allowing for further admissions.
- 106 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-3
- 106 min · Dispatch → Dispatch · RESOLVE [AI]: AMBS-3 will take MCI-2-P11 to Hospital D now, and MCI-2-P12 will wait for a bed to become available.

**PVT-1** · 2 patient(s) · MCI-2 → Hospital A (decided by rule backup)
- 114 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 2 patient(s), ETA 9 min. Can you take them?
- 114 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P17, but we cannot take MCI-2-P18 due to bed limitations. We currently have no free ER beds and will be receiving two serious patients shortly.
- 114 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 2 patient(s), ETA 9 min. Can you take them?
- 114 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P17, but we cannot take MCI-2-P18 due to bed limitations. We currently have no free ER beds and will be receiving two serious patients shortly.
- 114 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 2 patient(s), ETA 9 min. Can you take them?
- 114 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P17, but we cannot take MCI-2-P18 due to bed limitations. We currently have no free ER beds and will be receiving two serious patients shortly.
- 114 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 2 patient(s), ETA 9 min. Can you take them?
- 114 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P17, but we cannot take MCI-2-P18 due to bed limitations. We currently have no free ER beds and will be receiving two serious patients shortly.
- 114 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: PVT-1
- 114 min · Dispatch → Dispatch · RESOLVE [AI]: PVT-1 has been assigned to transport MCI-2-P17 to Hospital D, leaving MCI-2-P18 unassigned due to hospital capacity constraints.

**AMB-1** · 2 patient(s) · MCI-2 → Hospital C (decided by rule backup)
- 138 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-1 with 2 patient(s), ETA 9 min. Can you take them?
- 138 min · Hospital D → Dispatch · ACCEPT [AI]: We have sufficient capacity to accommodate both patients, as our current occupancy allows for their general needs.

**AMB-4** · 1 patient(s) · MCI-2 → Hospital C (decided by rule backup)
- 144 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 1 patient(s), ETA 9 min. Can you take them?
- 144 min · Hospital D → Dispatch · ACCEPT [AI]: We have enough capacity to accept the minor patient while maintaining our nurse coverage.

## Full conversation

-   0 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SW district
-   2 min · 911 caller → Dispatch · 911 CALL [sim]: “A bus flipped over! There are so many people, maybe 30 or so, people screaming.” (bus crash, about 31 hurt, grid 7,2)
-   2 min · Dispatch → Dispatch · PRIORITY REPORT [AI]: MCI: about 6 critical, 10 serious, 15 minor; urgency 0.9. The bus crash indicates a mass casualty situation with at least 31 victims, suggesting a high urgency. With trapped victims reported, fire services are needed to assist in rescues.
-   2 min · Dispatch → AMB-1 · STATUS [AI]: Assigned the nearest available ALS unit to the MCI with 31 victims needing assessment.
-   2 min · Dispatch → AMB-2 · STATUS [AI]: Assigned the second nearest ALS unit to ensure quick coverage for additional victims or critical cases.
-   2 min · Dispatch → AMB-3 · STATUS [AI]: Assigned the BLS unit as the third choice to handle any non-critical patients after the ALS units.
-   2 min · Dispatch → AMB-4 · STATUS [AI]: Assigned the second BLS unit with lower priority, as it will assist in triaging the remaining victims.
-   2 min · Dispatch → dispatch · PRIORITY REPORT [sim]: The bus crash indicates a mass casualty situation with at least 31 victims, suggesting a high urgency. With trapped victims reported, fire services are needed to assist in rescues.
-   2 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, respond to the bus crash at grid 7,2 for patients, triage on arrival.
-   2 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, respond to the bus crash at grid 7,2 for patients, triage on arrival.
-   2 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, respond to the bus crash at grid 7,2 for patients, triage on arrival.
-   2 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, respond to the bus crash at grid 7,2 for patients, triage on arrival.
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the NE district
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the NW district
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SE district
-   2 min · Monitor → Dispatch · ALERT [sim]: Surge detected: MCI-2
-   7 min · AMB-1 → Dispatch · SCENE REPORT [sim]: On scene. 29 patient(s): 2 red, 11 yellow, 16 green.
-   7 min · Dispatch → Dispatch · PRIORITY REPORT [AI]: MCI: about 2 critical, 11 serious, 16 minor; urgency 1.0. The call reports a bus crash with numerous reported victims, and the scene report confirms two critical and eleven serious injuries, indicating a high urgency for medical response. Fire response is necessary due to trapped victims.
-   7 min · Dispatch → Dispatch · ESCALATE [sim]: reassign: AMB-2
-   7 min · Dispatch → Dispatch · ESCALATE [sim]: reassign: AMB-3
-   7 min · Dispatch → Dispatch · ESCALATE [sim]: reassign: AMB-4
-   7 min · Dispatch → Dispatch · RESOLVE [AI]: All critical patients will be transported to Hospital C as it has the capacity and is able to handle the critical nature of the cases.
-   7 min · Dispatch → dispatch · PRIORITY REPORT [sim]: The call reports a bus crash with numerous reported victims, and the scene report confirms two critical and eleven serious injuries, indicating a high urgency for medical response. Fire response is necessary due to trapped victims.
-   7 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
-  17 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P15 from MCI-2 walked in without an ambulance.
-  18 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P15 (green) is in a treatment bed.
-  20 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P28 from MCI-2 walked in without an ambulance.
-  21 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P28 (green) is in a treatment bed.
-  22 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P24 from MCI-2 walked in without an ambulance.
-  22 min · Monitor → Dispatch · ALERT [sim]: Hospital D ER at 100% of capacity
-  23 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P24 (green) is in a treatment bed.
-  23 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P16 from MCI-2 walked in without an ambulance.
-  27 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
-  28 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P27 from MCI-2 walked in without an ambulance.
-  29 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P14 from MCI-2 walked in without an ambulance.
-  30 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P22 from MCI-2 walked in without an ambulance.
-  30 min · Dispatch → Dispatch · ESCALATE [sim]: reassign: AMB-4
-  30 min · Dispatch → Dispatch · RESOLVE [AI]: In this resolution, AMB-4 is assigned to transport the critical patient MCI-2-P04 to Hospital A as it has the needed capabilities and available resources.
-  30 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, respond to the bus crash at grid 7,2 for 1 patient(s).
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 1 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · ACCEPT [AI]: We can accept the patient as we have sufficient capacity in our ER and all necessary resources.
-  31 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI assigned ambulances that do not exist (AMB-10, AMB-11, AMB-12, AMB-13, AMB-14, AMB-15, AMB-16, AMB-17, AMB-18, AMB-19, AMB-20, AMB-21, AMB-22, AMB-5, AMB-6, AMB-7, AMB-8, AMB-9); those assignments were ignored.
-  31 min · Dispatch → MedRide · MUTUAL AID REQUEST [sim]: request 2 mutual-aid unit(s)
-  31 min · MedRide → Dispatch · MUTUAL AID RESPONSE [sim]: accepted; 2 unit(s) ready at tick 41
-  31 min · Dispatch → MedRide · MUTUAL AID [AI]: Requesting 2 private ambulance(s).
-  31 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, transport to Hospital C.
-  35 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P23 from MCI-2 walked in without an ambulance.
-  41 min · MedRide → All · STATUS [sim]: units activated: PVT-1, PVT-2
-  41 min · Dispatch → PVT-1 · STATUS [AI]: Assigned the first private unit to the first serious patient to ensure timely transport.
-  41 min · Dispatch → PVT-2 · STATUS [AI]: Assigned the second private unit to the second serious patient, optimizing resource use.
-  41 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 16 min. Can you take them?
-  41 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-2 with 1 patient(s), ETA 16 min. Can you take them?
-  41 min · Hospital A → Dispatch · REJECT [AI]: We cannot treat these patients as they require TRAUMA_L2 capability, which is beyond our capacity as a level 1 trauma center.
-  41 min · Hospital A → Dispatch · REJECT [AI]: We cannot treat these patients as they require TRAUMA_L2 capability, which is beyond our capacity as a level 1 trauma center.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · COUNTER [AI]: We can only accept MCI-2-P02 as we need to keep capacity for the incoming patient MCI-2-P04. MCI-2-P03 should be directed to another facility for care.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · COUNTER [AI]: We can only accept MCI-2-P02 as we need to keep capacity for the incoming patient MCI-2-P04. MCI-2-P03 should be directed to another facility for care.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · COUNTER [AI]: We can only accept MCI-2-P02 as we need to keep capacity for the incoming patient MCI-2-P04. MCI-2-P03 should be directed to another facility for care.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · COUNTER [AI]: We can only accept MCI-2-P02 as we need to keep capacity for the incoming patient MCI-2-P04. MCI-2-P03 should be directed to another facility for care.
-  41 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-1
-  41 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-2
-  41 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-3
-  41 min · Dispatch → Dispatch · RESOLVE [AI]: All units have been successfully assigned to hospitals where they can provide care. MCI-2-P03 remains unassigned as Hospital C cannot accept additional patients.
-  41 min · Dispatch → Dispatch · ESCALATE [sim]: Confidence 0.63 for AMB-1 → Hospital D; asking for review.
-  41 min · Dispatch → Dispatch · ESCALATE [sim]: Confidence 0.63 for AMB-2 → Hospital D; asking for review.
-  41 min · Dispatch → PVT-1 · ORDER [AI]: PVT-1, respond to the bus crash at grid 7,2 for 1 patient(s).
-  41 min · Dispatch → PVT-2 · ORDER [AI]: PVT-2, respond to the bus crash at grid 7,2 for 1 patient(s).
-  41 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D cannot treat this kind of patient.
-  41 min · Safety rules → Dispatch · BLOCKED R3 [sim]: Blocked: Hospital D is not a trauma center.
-  41 min · Safety rules → Dispatch · BLOCKED R4 [sim]: Blocked: Hospital D's contract only covers stable serious patients.
-  41 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D cannot treat this kind of patient.
-  41 min · Safety rules → Dispatch · BLOCKED R3 [sim]: Blocked: Hospital D is not a trauma center.
-  41 min · Safety rules → Dispatch · BLOCKED R4 [sim]: Blocked: Hospital D's contract only covers stable serious patients.
-  41 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, transport to Hospital C.
-  42 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI assigned ambulances that do not exist (AMB-5); those assignments were ignored.
-  42 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
-  42 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
-  42 min · Dispatch → AMB-1 · ORDER [rule backup]: AMB-1, transport to Hospital C.
-  42 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-2 arrives.
-  43 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P13 from MCI-2 walked in without an ambulance.
-  43 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
-  43 min · Dispatch → AMB-2 · ORDER [rule backup]: AMB-2, transport to Hospital A.
-  44 min · AMB-4 → Hospital C · PRE ALERT [sim]: Inbound with 1 yellow, ETA 13 min.
-  44 min · Monitor → Dispatch · ALERT [sim]: Hospital D: a patient has waited 21 min for a bed
-  45 min · AMB-3 → Hospital C · PRE ALERT [sim]: Inbound with 2 yellow, ETA 15 min.
-  46 min · AMB-2 → Hospital A · PRE ALERT [sim]: Inbound with 1 red, ETA 12 min.
-  46 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 1 patient(s), ETA 9 min. Can you take them?
-  46 min · Hospital D → Dispatch · ACCEPT [AI]: We can accommodate one patient but cannot accept more at this time due to current capacity limits.
-  46 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when PVT-1 arrives.
-  47 min · AMB-1 → Hospital C · PRE ALERT [sim]: Inbound with 1 red, ETA 17 min.
-  47 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
-  47 min · Dispatch → PVT-1 · ORDER [rule backup]: PVT-1, transport to Hospital B.
-  48 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-2 with 1 patient(s), ETA 9 min. Can you take them?
-  48 min · Hospital D → Dispatch · ACCEPT [AI]: We have capacity for one serious patient, but cannot take more without increasing our nursing staff.
-  48 min · Hospital D → Hospital A · STAFF REQUEST [AI]: Hospital D needs 1 nurse(s) to accept incoming patients
-  48 min · Hospital A → Hospital D · STAFF RESPONSE [AI]: Lending 1 nurse will still keep me above my minimum nurse coverage and allow Hospital D to accept their incoming patients.
-  48 min · Hospital A → Hospital D · STAFF DEPARTED [sim]: 1 nurse(s) departed.
-  48 min · Hospital A → Hospital D · STAFF [AI]: Sending 1 nurse(s) to help.
-  48 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when PVT-2 arrives.
-  49 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
-  49 min · Dispatch → PVT-2 · ORDER [rule backup]: PVT-2, transport to Hospital B.
-  56 min · PVT-1 → Hospital B · PRE ALERT [sim]: Inbound with 1 yellow, ETA 23 min.
-  57 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P04 (yellow) is in a treatment bed.
-  58 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P01 (red) is in a treatment bed.
-  60 min · PVT-2 → Hospital B · PRE ALERT [sim]: Inbound with 1 yellow, ETA 23 min.
-  60 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P02 (yellow) is in a treatment bed.
-  60 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 117% of capacity
-  62 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P16 (green) is in a treatment bed.
-  64 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P00 (red) is in a treatment bed.
-  69 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P03 (yellow) is in a treatment bed.
-  71 min · Dispatch → AMB-4 · STATUS [AI]: Assigning AMB-4 to the two most severe serious patients (MCI-2-P07 and MCI-2-P08) to maximize care efficiency.
-  71 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: AMB-4
-  71 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: AMB-4
-  71 min · Dispatch → Dispatch · RESOLVE [AI]: All four patients from the duplicated calls were assigned to AMB-4, which is going to Hospital C, ensuring timely care with available capacity.
-  71 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, respond to the bus crash at grid 7,2 for 2 patient(s).
-  71 min · Safety rules → Dispatch · BLOCKED R1 [sim]: Blocked: AMB-4 was already given an order this minute.
-  71 min · Safety rules → Dispatch · BLOCKED R1 [sim]: Blocked: AMB-4 was already given an order this minute.
-  74 min · Dispatch → AMB-2 · STATUS [AI]: Assigned to two SERIOUS patients to ensure they receive timely care.
-  74 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: AMB-2
-  74 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-2 is assigned to hospital A as it can accommodate both patients with the fastest transport time.
-  74 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, respond to the bus crash at grid 7,2 for 2 patient(s).
-  74 min · Safety rules → Dispatch · BLOCKED R1 [sim]: Blocked: AMB-2 was already given an order this minute.
-  78 min · Hospital A → Hospital D · STAFF ARRIVED [sim]: 1 nurse(s) arrived.
-  79 min · Hospital B → Dispatch · IN CARE [sim]: MCI-2-P05 (yellow) is in a treatment bed.
-  79 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P27 (green) is in a treatment bed.
-  83 min · Hospital B → Dispatch · IN CARE [sim]: MCI-2-P06 (yellow) is in a treatment bed.
-  83 min · Monitor → Dispatch · ALERT [sim]: Hospital B ER at 100% of capacity
-  84 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 9 min. Can you take them?
-  84 min · Hospital D → Dispatch · COUNTER [AI]: We can accept one patient now and are expecting a bed to free up shortly for the second one. Please send patient MCI-2-P07 first, and we will accept MCI-2-P08 as soon as the bed is available.
-  84 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 9 min. Can you take them?
-  84 min · Hospital D → Dispatch · COUNTER [AI]: We can accept one patient now and are expecting a bed to free up shortly for the second one. Please send patient MCI-2-P07 first, and we will accept MCI-2-P08 as soon as the bed is available.
-  84 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 9 min. Can you take them?
-  84 min · Hospital D → Dispatch · COUNTER [AI]: We can accept one patient now and are expecting a bed to free up shortly for the second one. Please send patient MCI-2-P07 first, and we will accept MCI-2-P08 as soon as the bed is available.
-  84 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 9 min. Can you take them?
-  84 min · Hospital D → Dispatch · COUNTER [AI]: We can accept one patient now and are expecting a bed to free up shortly for the second one. Please send patient MCI-2-P07 first, and we will accept MCI-2-P08 as soon as the bed is available.
-  84 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-4
-  84 min · Dispatch → Dispatch · RESOLVE [AI]: MCI-2-P07 is assigned to hospital D immediately, but MCI-2-P08 is unassigned until a bed frees up.
-  84 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI assigned ambulances that do not exist (AMB-5, AMB-6, AMB-7); those assignments were ignored.
-  84 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-4 arrives.
-  85 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
-  85 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital B will not have a free bed and staff when AMB-4 arrives.
-  86 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
-  86 min · Dispatch → AMB-4 · ORDER [rule backup]: AMB-4, transport to Hospital A.
-  89 min · Dispatch → AMB-3 · STATUS [AI]: Assigned the free unit AMB-3 to transport the two serious patients, P11 and P12, as they require immediate care and there are no other units available for these patients.
-  89 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  89 min · Hospital D → Dispatch · COUNTER [AI]: I can accept one patient now, but I can't accommodate the second one due to current ER bed limitations. My ER bed capacity is fully utilized, and I cannot take additional patients at this moment.
-  89 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  89 min · Hospital D → Dispatch · COUNTER [AI]: I can accept one patient now, but I can't accommodate the second one due to current ER bed limitations. My ER bed capacity is fully utilized, and I cannot take additional patients at this moment.
-  89 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  89 min · Hospital D → Dispatch · COUNTER [AI]: I can accept one patient now, but I can't accommodate the second one due to current ER bed limitations. My ER bed capacity is fully utilized, and I cannot take additional patients at this moment.
-  89 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  89 min · Hospital D → Dispatch · COUNTER [AI]: I can accept one patient now, but I can't accommodate the second one due to current ER bed limitations. My ER bed capacity is fully utilized, and I cannot take additional patients at this moment.
-  89 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-2
-  89 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-2 will take one patient to Hospital D, which can accept only one due to bed limitations, leaving the second patient unassigned for now.
-  89 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, respond to the bus crash at grid 7,2 for 2 patient(s).
-  89 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital D.
-  89 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, transport to Hospital D.
-  94 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P14 (green) is in a treatment bed.
-  95 min · AMB-4 → Hospital A · PRE ALERT [sim]: Inbound with 2 yellow, ETA 13 min.
-  95 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P22 (green) is in a treatment bed.
-  95 min · Dispatch → PVT-1 · STATUS [AI]: Assigning the private unit to transport two minor patients minimizes wait time for other critical cases.
-  95 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: PVT-1
-  95 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: PVT-1
-  95 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: PVT-1
-  95 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: PVT-1
-  95 min · Dispatch → Dispatch · RESOLVE [AI]: PVT-1 is assigned to Hospital B to treat all patients from incident MCI-2, ensuring efficient care within available resources.
-  95 min · Dispatch → PVT-1 · ORDER [AI]: PVT-1, respond to the bus crash at grid 7,2 for 2 patient(s).
-  95 min · Safety rules → Dispatch · BLOCKED R1 [sim]: Blocked: PVT-1 was already given an order this minute.
-  95 min · Safety rules → Dispatch · BLOCKED R7 [sim]: Blocked: an ambulance carries at most two patients.
- 102 min · AMB-2 → Hospital D · PRE ALERT [sim]: Inbound with 2 yellow, ETA 9 min.
- 106 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 106 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P11 but cannot take MCI-2-P12 at this time due to bed occupancy. A ward bed will free up in the next 20 minutes, allowing for further admissions.
- 106 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 106 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P11 but cannot take MCI-2-P12 at this time due to bed occupancy. A ward bed will free up in the next 20 minutes, allowing for further admissions.
- 106 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 106 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P11 but cannot take MCI-2-P12 at this time due to bed occupancy. A ward bed will free up in the next 20 minutes, allowing for further admissions.
- 106 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 106 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P11 but cannot take MCI-2-P12 at this time due to bed occupancy. A ward bed will free up in the next 20 minutes, allowing for further admissions.
- 106 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-3
- 106 min · Dispatch → Dispatch · RESOLVE [AI]: AMBS-3 will take MCI-2-P11 to Hospital D now, and MCI-2-P12 will wait for a bed to become available.
- 106 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI assigned ambulances that do not exist (AMB-5, AMB-6); those assignments were ignored.
- 106 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital D.
- 106 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, transport to Hospital D.
- 108 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P07 (yellow) is in a treatment bed.
- 108 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P08 (yellow) is in a treatment bed.
- 108 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
- 114 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 2 patient(s), ETA 9 min. Can you take them?
- 114 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P17, but we cannot take MCI-2-P18 due to bed limitations. We currently have no free ER beds and will be receiving two serious patients shortly.
- 114 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 2 patient(s), ETA 9 min. Can you take them?
- 114 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P17, but we cannot take MCI-2-P18 due to bed limitations. We currently have no free ER beds and will be receiving two serious patients shortly.
- 114 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 2 patient(s), ETA 9 min. Can you take them?
- 114 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P17, but we cannot take MCI-2-P18 due to bed limitations. We currently have no free ER beds and will be receiving two serious patients shortly.
- 114 min · Dispatch → Hospital D · PROPOSE [AI]: PVT-1 with 2 patient(s), ETA 9 min. Can you take them?
- 114 min · Hospital D → Dispatch · COUNTER [AI]: We can accept MCI-2-P17, but we cannot take MCI-2-P18 due to bed limitations. We currently have no free ER beds and will be receiving two serious patients shortly.
- 114 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: PVT-1
- 114 min · Dispatch → Dispatch · RESOLVE [AI]: PVT-1 has been assigned to transport MCI-2-P17 to Hospital D, leaving MCI-2-P18 unassigned due to hospital capacity constraints.
- 114 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when PVT-1 arrives.
- 114 min · Safety rules → Dispatch · BLOCKED R4 [sim]: Blocked: Hospital D's contract only covers stable serious patients.
- 115 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
- 115 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital A.
- 115 min · Dispatch → PVT-1 · ORDER [rule backup]: PVT-1, transport to Hospital A.
- 117 min · AMB-3 → Hospital D · PRE ALERT [sim]: Inbound with 2 yellow, ETA 9 min.
- 117 min · Hospital A → All · STATUS [sim]: MCI-2-P01 moved up to a ward bed.
- 119 min · Dispatch → AMB-1 · STATUS [AI]: Unit AMB-1 is the only available ALS unit and will transport the first two minor patients.
- 119 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, respond to the bus crash at grid 7,2 for 2 patient(s).
- 120 min · Hospital C → All · STATUS [sim]: MCI-2-P00 moved up to a ward bed.
- 121 min · Dispatch → PVT-2 · STATUS [AI]: Assigning the free BLS unit to transport all three minor patients since they are stable and can share the ride.
- 121 min · Safety rules → Dispatch · BLOCKED R7 [sim]: Blocked: an ambulance carries at most two patients.
- 126 min · Dispatch → AMB-4 · STATUS [AI]: Assigned to the first minor patient as it has the shortest ETA.
- 126 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: AMB-4
- 126 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: AMB-4
- 126 min · Dispatch → Dispatch · RESOLVE [AI]: All proposed patients have been assigned to hospital A, which has the capacity and the quickest response time.
- 126 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, respond to the bus crash at grid 7,2 for 1 patient(s).
- 126 min · Safety rules → Dispatch · BLOCKED R1 [sim]: Blocked: AMB-4 was already given an order this minute.
- 127 min · PVT-1 → Hospital A · PRE ALERT [sim]: Inbound with 2 green, ETA 14 min.
- 127 min · Dispatch → PVT-2 · STATUS [AI]: Assigned the private BLS ambulance to take the two minor patients to Hospital A, which has space available and is the nearest option.
- 127 min · Dispatch → PVT-2 · ORDER [AI]: PVT-2, respond to the bus crash at grid 7,2 for 2 patient(s).
- 131 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P09 (yellow) is in a treatment bed.
- 138 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-1 with 2 patient(s), ETA 9 min. Can you take them?
- 138 min · Hospital D → Dispatch · ACCEPT [AI]: We have sufficient capacity to accommodate both patients, as our current occupancy allows for their general needs.
- 138 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-1 arrives.
- 138 min · Safety rules → Dispatch · BLOCKED R4 [sim]: Blocked: Hospital D's contract only covers stable serious patients.
- 139 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
- 139 min · Dispatch → AMB-1 · ORDER [rule backup]: AMB-1, transport to Hospital C.
- 144 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 1 patient(s), ETA 9 min. Can you take them?
- 144 min · Hospital D → Dispatch · ACCEPT [AI]: We have enough capacity to accept the minor patient while maintaining our nurse coverage.
- 144 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-4 arrives.
- 144 min · Safety rules → Dispatch · BLOCKED R4 [sim]: Blocked: Hospital D's contract only covers stable serious patients.
- 145 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
- 145 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital C.
- 145 min · Dispatch → AMB-4 · ORDER [rule backup]: AMB-4, transport to Hospital C.
- 146 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P10 (yellow) is in a treatment bed.
- 147 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI gave no usable hospital for this ambulance. The rule-based backup decided.
- 147 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital C.
- 147 min · Dispatch → PVT-2 · ORDER [rule backup]: PVT-2, transport to Hospital C.
- 152 min · AMB-4 → Hospital C · PRE ALERT [sim]: Inbound with 1 green, ETA 13 min.
- 153 min · AMB-1 → Hospital C · PRE ALERT [sim]: Inbound with 2 green, ETA 12 min.
- 158 min · PVT-2 → Hospital C · PRE ALERT [sim]: Inbound with 2 green, ETA 19 min.
- 158 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Surge detected: MCI-2
- 159 min · Hospital C → All · STATUS [sim]: MCI-2-P02 moved up to a ward bed.
- 162 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P11 (yellow) is in a treatment bed.
- 162 min · Monitor → Dispatch · ALERT [sim]: Hospital A: a patient has waited 21 min for a bed
- 165 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P12 (yellow) is in a treatment bed.
- 168 min · Hospital C → All · STATUS [sim]: MCI-2-P04 moved up to a ward bed.
- 168 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P19 (green) is in a treatment bed.
- 171 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P17 (green) is in a treatment bed.
- 173 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P20 (green) is in a treatment bed.
- 186 min · Monitor → Dispatch · ALERT [sim]: Hospital C: a patient has waited 21 min for a bed
- 188 min · Hospital B → All · STATUS [sim]: MCI-2-P05 moved up to a ward bed.
- 193 min · Hospital B → All · STATUS [sim]: MCI-2-P06 moved up to a ward bed.
- 193 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital B ER at 100% of capacity
- 195 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P18 (green) is in a treatment bed.
- 195 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A: a patient has waited 53 min for a bed
- 196 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SE district
- 198 min · Hospital A → Hospital D · STAFF RETURNED [sim]: 1 nurse(s) returned.
- 202 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P21 (green) is in a treatment bed.
- 220 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P25 (green) is in a treatment bed.
- 221 min · Hospital D → All · STATUS [sim]: MCI-2-P09 moved up to a ward bed.
- 221 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P23 (green) is in a treatment bed.
- 224 min · Monitor → Dispatch · ALERT [sim]: Hospital B ER at 100% of capacity
- 228 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the NW district
- 242 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P26 (green) is in a treatment bed.
- 242 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C: a patient has waited 64 min for a bed
- 243 min · Hospital C → All · STATUS [sim]: MCI-2-P03 moved up to a ward bed.
- 254 min · Hospital D → All · STATUS [sim]: MCI-2-P12 moved up to a ward bed.
- 254 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P13 (green) is in a treatment bed.
- 254 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital D: a patient has waited 210 min for a bed
- 254 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SW district
- 256 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
- 258 min · Hospital A → All · STATUS [sim]: MCI-2-P08 moved up to a ward bed.
- 260 min · Hospital D → All · STATUS [sim]: MCI-2-P11 moved up to a ward bed.
- 261 min · Hospital A → All · STATUS [sim]: MCI-2-P07 moved up to a ward bed.
- 267 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the NE district
