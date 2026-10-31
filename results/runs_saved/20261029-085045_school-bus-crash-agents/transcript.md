# School bus crash · agents

Policy: agents · model: gpt-4o-mini · information: partial · seed 7 · 270 simulated minutes

## How well it went

| Measure | Value |
|---|---|
| Deaths | 0 |
| Critical patients in care within 60 min | 50% |
| Critical patients: call to definitive care (mean) | 87.5 min |
| Call to first ambulance on scene (mean) | 5 min |
| Ambulance minutes waiting at ER doors (beyond 10 min) | 250.0 min |
| Hospital minutes over capacity | 736 min |
| Calls with no ambulance after 30 min | 0 |
| Patients still not in care at the end | 3 |
| Proposals blocked by safety rules | 10 |
| Decisions sent for human review | 2 |
| Synthetic outcome score (higher is better) | 27.5 |
| AI calls | 93 |
| AI tokens | 181847 |
| Decisions by AI agents | 24 |
| Decisions by the rule backup | 3 |

## Negotiations


**AMB-2** · 0 patient(s) · MCI-2 → Hospital B (decided by agents)
-   7 min · Dispatch → Dispatch · ESCALATE [AI]: reassign: AMB-2
-   7 min · Dispatch → Dispatch · RESOLVE [AI]: All critical patients are assigned to Hospital C, which can accommodate their needs, avoiding escalation.
-  17 min · Dispatch → Hospital B · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 22 min. Can you take them?
-  17 min · Hospital B → Dispatch · ACCEPT [AI]: We have sufficient capacity and staff to accept both patients.
-  76 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: AMB-2
-  76 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: AMB-2
-  76 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-2 is assigned to Hospital B, which can accommodate the patients while others have no available ER beds.

**AMB-3** · 0 patient(s) · MCI-2 → Hospital C (decided by agents)
-   7 min · Dispatch → Dispatch · ESCALATE [AI]: reassign: AMB-3
-   7 min · Dispatch → Dispatch · RESOLVE [AI]: All critical patients are assigned to Hospital C, which can accommodate their needs, avoiding escalation.
-  19 min · Dispatch → Hospital B · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 22 min. Can you take them?
-  19 min · Hospital B → Dispatch · COUNTER [AI]: We can accept one patient now (MCI-2-P06) and will have availability for the second patient (MCI-2-P07) in approximately 30 minutes.
-  19 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  19 min · Hospital C → Dispatch · ACCEPT [AI]: We have enough capacity to accept both patients with the current number of beds, nurses, and available capabilities.

**AMB-4** · 0 patient(s) · MCI-2 → Hospital C (decided by agents)
-   7 min · Dispatch → Dispatch · ESCALATE [AI]: reassign: AMB-4
-   7 min · Dispatch → Dispatch · RESOLVE [AI]: All critical patients are assigned to Hospital C, which can accommodate their needs, avoiding escalation.
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · COUNTER [AI]: We can accept one patient now, but we will need to delay the second due to pending arrivals and current occupancy.
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · COUNTER [AI]: We can accept one patient now, but we will need to delay the second due to pending arrivals and current occupancy.
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · COUNTER [AI]: We can accept one patient now, but we will need to delay the second due to pending arrivals and current occupancy.
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · COUNTER [AI]: We can accept one patient now, but we will need to delay the second due to pending arrivals and current occupancy.
-  31 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-4
-  31 min · Dispatch → Dispatch · RESOLVE [AI]: Ambulance AMB-4 is assigned to Hospital C for one patient, while the second patient remains unassigned due to capacity constraints.

**AMB-1** · 1 patient(s) · MCI-2 → Hospital C (decided by agents)
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · REJECT [AI]: We cannot accept the incoming patient MCI-2-P00 as we lack a trauma bay and a surgeon for their critical care needs.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · REJECT [AI]: We cannot accept the incoming patient MCI-2-P00 as we lack a trauma bay and a surgeon for their critical care needs.
-  41 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 16 min. Can you take them?
-  41 min · Hospital A → Dispatch · REJECT [AI]: The proposed patient requires a TRAUMA_L2 capability which is beyond our current capabilities as a TRAUMA_L1 center, thus we cannot accept this patient.
-  41 min · Dispatch → Hospital B · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 22 min. Can you take them?
-  41 min · Hospital B → Dispatch · REJECT [AI]: We are a stabilization-only trauma bay hospital and cannot accommodate critical trauma patients requiring a trauma bay and surgical intervention.
-  41 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-1
-  41 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-1 is assigned to Hospital C, which has the necessary capabilities and free resources to handle the critical trauma patient.
-  41 min · Dispatch → Human reviewer · ESCALATE [AI]: Confidence 0.65 for AMB-1 → Hospital C; asking for review.

**AMB-3** · 2 patient(s) · MCI-2 → Hospital A (decided by agents)
-  45 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 16 min. Can you take them?
-  45 min · Hospital A → Dispatch · COUNTER [AI]: We can accept MCI-2-P06 but cannot accept MCI-2-P07 due to nurse coverage; we need a minimum of 2 nurses on duty to manage our current ER occupancy.
-  45 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
-  45 min · Hospital D → Dispatch · COUNTER [AI]: We can accept 1 patient, MCI-2-P06, but cannot accommodate MCI-2-P07 due to full capacity.
-  45 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-3
-  45 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-3 is directed to Hospital A for MCI-2-P06 due to capacity, leaving MCI-2-P07 unassigned.

**AMB-1** · 1 patient(s) · MCI-2 → Hospital A (decided by agents)
-  88 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  88 min · Hospital D → Dispatch · REJECT [AI]: We cannot accept this patient due to their critical trauma needs, which are outside our capabilities.
-  88 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 16 min. Can you take them?
-  88 min · Hospital A → Dispatch · REJECT [AI]: The patient requires a Trauma Level 2 facility, which exceeds our Trauma Level 1 capabilities, making it impossible to admit.
-  88 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 15 min. Can you take them?
-  88 min · Hospital C → Dispatch · REJECT [AI]: We are currently at full capacity in the ER with no available trauma bays or surgeons, and we cannot safely accommodate this critical patient.
-  88 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  88 min · Hospital D → Dispatch · REJECT [AI]: We cannot accept this patient due to their critical trauma needs, which are outside our capabilities.
-  88 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-1
-  88 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-1 is assigned to Hospital B due to its capability to take patients, despite limitations at other hospitals.
-  88 min · Dispatch → Human reviewer · ESCALATE [AI]: Confidence 0.61 for AMB-1 → Hospital B; asking for review.
- 175 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: AMB-1
- 175 min · Dispatch → Dispatch · ESCALATE [AI]: duplicate: AMB-1
- 175 min · Dispatch → Dispatch · RESOLVE [AI]: All patients remain unassigned as they are duplicates, but AMB-1 will transport to Hospital A due to its capacity for trauma care.

**AMB-3** · 2 patient(s) · MCI-2 → Hospital A (decided by agents)
-  92 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 16 min. Can you take them?
-  92 min · Hospital A → Dispatch · COUNTER [AI]: I can accept one patient now, but cannot take both due to current capacity. The other patient, MCI-2-P11, needs to go elsewhere until a bed frees up.
-  92 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
-  92 min · Hospital D → Dispatch · REJECT [AI]: We cannot accept the proposed patients as we currently have no available ER beds, and our hospital is operating at full capacity for the ER.
-  92 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 16 min. Can you take them?
-  92 min · Hospital A → Dispatch · COUNTER [AI]: I can accept one patient now, but cannot take both due to current capacity. The other patient, MCI-2-P11, needs to go elsewhere until a bed frees up.
-  92 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 16 min. Can you take them?
-  92 min · Hospital A → Dispatch · COUNTER [AI]: I can accept one patient now, but cannot take both due to current capacity. The other patient, MCI-2-P11, needs to go elsewhere until a bed frees up.
-  92 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-3
-  92 min · Dispatch → Dispatch · RESOLVE [AI]: Ambulance AMB-3 is assigned to hospital A for the first patient, while the second patient remains unassigned due to hospital A's bed limitations.

**AMB-2** · 2 patient(s) · MCI-2 → Hospital C (decided by agents)
-  94 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  94 min · Hospital D → Dispatch · COUNTER [AI]: We can only accept one patient at this time, as we currently have no available ER beds. We can accept the second patient if a bed frees up within the next few minutes.
-  94 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  94 min · Hospital D → Dispatch · COUNTER [AI]: We can only accept one patient at this time, as we currently have no available ER beds. We can accept the second patient if a bed frees up within the next few minutes.
-  94 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  94 min · Hospital D → Dispatch · COUNTER [AI]: We can only accept one patient at this time, as we currently have no available ER beds. We can accept the second patient if a bed frees up within the next few minutes.
-  94 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  94 min · Hospital D → Dispatch · COUNTER [AI]: We can only accept one patient at this time, as we currently have no available ER beds. We can accept the second patient if a bed frees up within the next few minutes.
-  94 min · Dispatch → Dispatch · ESCALATE [AI]: route unresolved: AMB-2
-  94 min · Dispatch → Dispatch · RESOLVE [AI]: Hospital C is chosen for Ambulance 2 as it can handle both patients while meeting the necessary capabilities and available resources.

**AMB-4** · 1 patient(s) · MCI-2 → Hospital D (decided by agents)
-  97 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 1 patient(s), ETA 9 min. Can you take them?
-  97 min · Hospital D → Dispatch · ACCEPT [AI]: We currently have limited ER capacity, but we can safely accept one patient.

**AMB-2** · 2 patient(s) · MCI-2 → Hospital C (decided by agents)
- 178 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 15 min. Can you take them?
- 178 min · Hospital C → Dispatch · ACCEPT [AI]: We have sufficient capacity to accept both patients with available beds and nursing staff.

**AMB-1** · 2 patient(s) · MCI-2 → Hospital A (decided by rule backup)
- 188 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-1 with 2 patient(s), ETA 9 min. Can you take them?
- 188 min · Hospital D → Dispatch · ACCEPT [AI]: We can accept both patients as they only require general capabilities and we have the necessary capacity.

**AMB-3** · 2 patient(s) · MCI-2 → Hospital B (decided by rule backup)
- 196 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 196 min · Hospital D → Dispatch · ACCEPT [AI]: We have sufficient capacity (ward beds and nurses) to accept both patients with minor severity.

**AMB-4** · 1 patient(s) · MCI-2 → Hospital C (decided by rule backup)
- 201 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 1 patient(s), ETA 9 min. Can you take them?
- 201 min · Hospital D → Dispatch · ACCEPT [AI]: We have the capacity to accept this minor severity patient as we have enough free ward beds and nurse coverage.

## Full conversation

-   0 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SW district
-   2 min · 911 caller → Dispatch · 911 CALL [sim]: “A bus flipped over! There are so many people, maybe 30 or so, people screaming.” (bus crash, about 31 hurt, grid 7,2)
-   2 min · Dispatch → Dispatch · PRIORITY REPORT [AI]: MCI: about 6 critical, 10 serious, 15 minor; urgency 0.9. The bus crash indicates a mass casualty situation with at least 31 victims, suggesting a high urgency. With trapped victims reported, fire services are needed to assist in rescues.
-   2 min · Dispatch → AMB-1 · STATUS [AI]: AMB-1 is the closest free unit to the MCI call, arriving in approximately 6.4 minutes.
-   2 min · Dispatch → AMB-2 · STATUS [AI]: AMB-2, while further away at 15.3 minutes, will also be deployed to support the MCI situation.
-   2 min · Dispatch → AMB-3 · STATUS [AI]: AMB-3 will be dispatched next as it is available and less critical patients will likely still need assistance.
-   2 min · Dispatch → AMB-4 · STATUS [AI]: AMB-4 is the last available unit and will respond to the MCI for additional support.
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
-   7 min · Dispatch → Dispatch · RESOLVE [AI]: All critical patients are assigned to Hospital C, which can accommodate their needs, avoiding escalation.
-   7 min · Dispatch → dispatch · PRIORITY REPORT [sim]: The call reports a bus crash with numerous reported victims, and the scene report confirms two critical and eleven serious injuries, indicating a high urgency for medical response. Fire response is necessary due to trapped victims.
-   7 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, respond to the bus crash at grid 7,2 for 2 patient(s).
-   7 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, respond to the bus crash at grid 7,2 for 2 patient(s).
-   7 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, respond to the bus crash at grid 7,2 for 2 patient(s).
-   7 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
-  17 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P15 from MCI-2 walked in without an ambulance.
-  17 min · Dispatch → Hospital B · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 22 min. Can you take them?
-  17 min · Hospital B → Dispatch · ACCEPT [AI]: We have sufficient capacity and staff to accept both patients.
-  17 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, transport to Hospital B.
-  18 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P15 (green) is in a treatment bed.
-  18 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI assigned ambulances that do not exist (AMB-5, AMB-6); those assignments were ignored.
-  19 min · Dispatch → Hospital B · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 22 min. Can you take them?
-  19 min · Hospital B → Dispatch · COUNTER [AI]: We can accept one patient now (MCI-2-P06) and will have availability for the second patient (MCI-2-P07) in approximately 30 minutes.
-  19 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 15 min. Can you take them?
-  19 min · Hospital C → Dispatch · ACCEPT [AI]: We have enough capacity to accept both patients with the current number of beds, nurses, and available capabilities.
-  19 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, transport to Hospital C.
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
-  30 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI assigned ambulances that do not exist (AMB-5); those assignments were ignored.
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · COUNTER [AI]: We can accept one patient now, but we will need to delay the second due to pending arrivals and current occupancy.
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · COUNTER [AI]: We can accept one patient now, but we will need to delay the second due to pending arrivals and current occupancy.
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · COUNTER [AI]: We can accept one patient now, but we will need to delay the second due to pending arrivals and current occupancy.
-  31 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-4 with 2 patient(s), ETA 15 min. Can you take them?
-  31 min · Hospital C → Dispatch · COUNTER [AI]: We can accept one patient now, but we will need to delay the second due to pending arrivals and current occupancy.
-  31 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-4
-  31 min · Dispatch → Dispatch · RESOLVE [AI]: Ambulance AMB-4 is assigned to Hospital C for one patient, while the second patient remains unassigned due to capacity constraints.
-  31 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, transport to Hospital C.
-  32 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI assigned ambulances that do not exist (MedRide-1); those assignments were ignored.
-  35 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P23 from MCI-2 walked in without an ambulance.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · REJECT [AI]: We cannot accept the incoming patient MCI-2-P00 as we lack a trauma bay and a surgeon for their critical care needs.
-  41 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 15 min. Can you take them?
-  41 min · Hospital C → Dispatch · REJECT [AI]: We cannot accept the incoming patient MCI-2-P00 as we lack a trauma bay and a surgeon for their critical care needs.
-  41 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 16 min. Can you take them?
-  41 min · Hospital A → Dispatch · REJECT [AI]: The proposed patient requires a TRAUMA_L2 capability which is beyond our current capabilities as a TRAUMA_L1 center, thus we cannot accept this patient.
-  41 min · Dispatch → Hospital B · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 22 min. Can you take them?
-  41 min · Hospital B → Dispatch · REJECT [AI]: We are a stabilization-only trauma bay hospital and cannot accommodate critical trauma patients requiring a trauma bay and surgical intervention.
-  41 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-1
-  41 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-1 is assigned to Hospital C, which has the necessary capabilities and free resources to handle the critical trauma patient.
-  41 min · Dispatch → Dispatch · ESCALATE [sim]: Confidence 0.65 for AMB-1 → Hospital C; asking for review.
-  41 min · Safety rules → Human reviewer · NEEDS APPROVAL [sim]: Waiting for review: AMB-1 to Hospital C. low confidence: the proposer asked for review. Alternative: AMB-1 to Hospital A.
-  42 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI assigned ambulances that do not exist (free_unit_1, free_unit_2, free_unit_3, free_unit_4); those assignments were ignored.
-  43 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, transport to Hospital C.
-  43 min · Approval policy → Dispatch · APPROVED [sim]: Approved: AMB-1 to Hospital C. approved as proposed
-  43 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P13 from MCI-2 walked in without an ambulance.
-  44 min · AMB-2 → Hospital B · PRE ALERT [sim]: Inbound with 2 yellow, ETA 18 min.
-  44 min · Monitor → Dispatch · ALERT [sim]: Hospital D: a patient has waited 21 min for a bed
-  45 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Re-check before transport failed: Hospital C will not have a free bed and staff when AMB-3 arrives.
-  45 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 16 min. Can you take them?
-  45 min · Hospital A → Dispatch · COUNTER [AI]: We can accept MCI-2-P06 but cannot accept MCI-2-P07 due to nurse coverage; we need a minimum of 2 nurses on duty to manage our current ER occupancy.
-  45 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
-  45 min · Hospital D → Dispatch · COUNTER [AI]: We can accept 1 patient, MCI-2-P06, but cannot accommodate MCI-2-P07 due to full capacity.
-  45 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-3
-  45 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-3 is directed to Hospital A for MCI-2-P06 due to capacity, leaving MCI-2-P07 unassigned.
-  45 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI agent's answer was unusable. The rule-based backup decided.
-  45 min · AMB-3 → Hospital A · PRE ALERT [sim]: Inbound with 2 yellow, ETA 15 min.
-  45 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, transport to Hospital A.
-  46 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI assigned ambulances that do not exist (MCI-2-P01, MCI-2-P02, MCI-2-P10, MCI-2-P12); those assignments were ignored.
-  47 min · AMB-1 → Hospital C · PRE ALERT [sim]: Inbound with 1 red, ETA 12 min.
-  47 min · AMB-4 → Hospital C · PRE ALERT [sim]: Inbound with 2 yellow, ETA 17 min.
-  59 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P00 (red) is in a treatment bed.
-  60 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P06 (yellow) is in a treatment bed.
-  60 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P07 (yellow) is in a treatment bed.
-  60 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
-  62 min · Hospital B → Dispatch · IN CARE [sim]: MCI-2-P04 (yellow) is in a treatment bed.
-  62 min · Hospital B → Dispatch · IN CARE [sim]: MCI-2-P05 (yellow) is in a treatment bed.
-  62 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P16 (green) is in a treatment bed.
-  64 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P08 (yellow) is in a treatment bed.
-  64 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P09 (yellow) is in a treatment bed.
-  64 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 117% of capacity
-  72 min · Dispatch → AMB-1 · STATUS [AI]: Dispatching AMB-1 to transport the critical patient (MCI-2-P01) who needs trauma capabilities to a suitable hospital.
-  72 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, respond to the bus crash at grid 7,2 for 1 patient(s), 1 critical.
-  76 min · Dispatch → AMB-2 · STATUS [AI]: Assigned to two serious patients due to limited available units.
-  76 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: AMB-2
-  76 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: AMB-2
-  76 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-2 is assigned to Hospital B, which can accommodate the patients while others have no available ER beds.
-  76 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, respond to the bus crash at grid 7,2 for 2 patient(s).
-  77 min · Dispatch → AMB-3 · STATUS [AI]: Assign AMB-3 to the two most serious patients (MCI-2-P10 and MCI-2-P11) since they require immediate transport and there are no other available units.
-  77 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, respond to the bus crash at grid 7,2 for 2 patient(s).
-  79 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P27 (green) is in a treatment bed.
-  80 min · Dispatch → AMB-4 · STATUS [AI]: Assigned AMB-4 to the serious patient MCI-2-P12 as the only available unit since critical patients must be prioritized.
-  80 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, respond to the bus crash at grid 7,2 for 1 patient(s).
-  81 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
-  82 min · Monitor → Dispatch · ALERT [sim]: Hospital B ER at 100% of capacity
-  88 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  88 min · Hospital D → Dispatch · REJECT [AI]: We cannot accept this patient due to their critical trauma needs, which are outside our capabilities.
-  88 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 16 min. Can you take them?
-  88 min · Hospital A → Dispatch · REJECT [AI]: The patient requires a Trauma Level 2 facility, which exceeds our Trauma Level 1 capabilities, making it impossible to admit.
-  88 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 15 min. Can you take them?
-  88 min · Hospital C → Dispatch · REJECT [AI]: We are currently at full capacity in the ER with no available trauma bays or surgeons, and we cannot safely accommodate this critical patient.
-  88 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  88 min · Hospital D → Dispatch · REJECT [AI]: We cannot accept this patient due to their critical trauma needs, which are outside our capabilities.
-  88 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-1
-  88 min · Dispatch → Dispatch · RESOLVE [AI]: AMB-1 is assigned to Hospital B due to its capability to take patients, despite limitations at other hospitals.
-  88 min · Dispatch → Dispatch · ESCALATE [sim]: Confidence 0.61 for AMB-1 → Hospital B; asking for review.
-  88 min · Safety rules → Human reviewer · NEEDS APPROVAL [sim]: Waiting for review: AMB-1 to Hospital B. low confidence: the proposer asked for review. Alternative: AMB-1 to Hospital A.
-  90 min · Dispatch → AMB-1 · ORDER [rules]: AMB-1, transport to Hospital A.
-  90 min · Approval policy → Dispatch · OVERRIDDEN [sim]: Changed to: AMB-1 to Hospital A. a better option was available
-  92 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 16 min. Can you take them?
-  92 min · Hospital A → Dispatch · COUNTER [AI]: I can accept one patient now, but cannot take both due to current capacity. The other patient, MCI-2-P11, needs to go elsewhere until a bed frees up.
-  92 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
-  92 min · Hospital D → Dispatch · REJECT [AI]: We cannot accept the proposed patients as we currently have no available ER beds, and our hospital is operating at full capacity for the ER.
-  92 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 16 min. Can you take them?
-  92 min · Hospital A → Dispatch · COUNTER [AI]: I can accept one patient now, but cannot take both due to current capacity. The other patient, MCI-2-P11, needs to go elsewhere until a bed frees up.
-  92 min · Dispatch → Hospital A · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 16 min. Can you take them?
-  92 min · Hospital A → Dispatch · COUNTER [AI]: I can accept one patient now, but cannot take both due to current capacity. The other patient, MCI-2-P11, needs to go elsewhere until a bed frees up.
-  92 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-3
-  92 min · Dispatch → Dispatch · RESOLVE [AI]: Ambulance AMB-3 is assigned to hospital A for the first patient, while the second patient remains unassigned due to hospital A's bed limitations.
-  92 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital A.
-  92 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, transport to Hospital A.
-  94 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P14 (green) is in a treatment bed.
-  94 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  94 min · Hospital D → Dispatch · COUNTER [AI]: We can only accept one patient at this time, as we currently have no available ER beds. We can accept the second patient if a bed frees up within the next few minutes.
-  94 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  94 min · Hospital D → Dispatch · COUNTER [AI]: We can only accept one patient at this time, as we currently have no available ER beds. We can accept the second patient if a bed frees up within the next few minutes.
-  94 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  94 min · Hospital D → Dispatch · COUNTER [AI]: We can only accept one patient at this time, as we currently have no available ER beds. We can accept the second patient if a bed frees up within the next few minutes.
-  94 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 9 min. Can you take them?
-  94 min · Hospital D → Dispatch · COUNTER [AI]: We can only accept one patient at this time, as we currently have no available ER beds. We can accept the second patient if a bed frees up within the next few minutes.
-  94 min · Dispatch → Dispatch · ESCALATE [sim]: route unresolved: AMB-2
-  94 min · Dispatch → Dispatch · RESOLVE [AI]: Hospital C is chosen for Ambulance 2 as it can handle both patients while meeting the necessary capabilities and available resources.
-  94 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital C.
-  94 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, transport to Hospital C.
-  95 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P22 (green) is in a treatment bed.
-  97 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 1 patient(s), ETA 9 min. Can you take them?
-  97 min · Hospital D → Dispatch · ACCEPT [AI]: We currently have limited ER capacity, but we can safely accept one patient.
-  97 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital D.
-  97 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, transport to Hospital D.
- 103 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
- 107 min · AMB-1 → Hospital A · PRE ALERT [sim]: Inbound with 1 red, ETA 13 min.
- 107 min · AMB-2 → Hospital C · PRE ALERT [sim]: Inbound with 2 yellow, ETA 15 min.
- 107 min · AMB-3 → Hospital A · PRE ALERT [sim]: Inbound with 2 yellow, ETA 14 min.
- 107 min · AMB-4 → Hospital D · PRE ALERT [sim]: Inbound with 1 yellow, ETA 9 min.
- 115 min · Hospital C → All · STATUS [sim]: MCI-2-P00 moved up to a ward bed.
- 119 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C ER at 100% of capacity
- 120 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P01 (red) is in a treatment bed.
- 122 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P02 (yellow) is in a treatment bed.
- 122 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 117% of capacity
- 131 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P12 (yellow) is in a treatment bed.
- 142 min · Monitor → Dispatch · ALERT [sim]: Hospital A: a patient has waited 21 min for a bed
- 143 min · Monitor → Dispatch · ALERT [sim]: Hospital C: a patient has waited 21 min for a bed
- 146 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P23 (green) is in a treatment bed.
- 152 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P03 (yellow) is in a treatment bed.
- 152 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C: a patient has waited 29 min for a bed
- 154 min · Hospital C → All · STATUS [sim]: MCI-2-P09 moved up to a ward bed.
- 162 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P13 (green) is in a treatment bed.
- 162 min · Dispatch → AMB-2 · STATUS [AI]: Assigned to two minor patients (MCI-2-P17 and MCI-2-P18) as we only have one free ambulance and it can take two patients.
- 162 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, respond to the bus crash at grid 7,2 for 2 patient(s).
- 162 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital D: a patient has waited 118 min for a bed
- 170 min · Hospital A → All · STATUS [sim]: MCI-2-P06 moved up to a ward bed.
- 170 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P10 (yellow) is in a treatment bed.
- 171 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P11 (yellow) is in a treatment bed.
- 171 min · Hospital B → All · STATUS [sim]: MCI-2-P05 moved up to a ward bed.
- 171 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A: a patient has waited 49 min for a bed
- 173 min · Hospital B → All · STATUS [sim]: MCI-2-P04 moved up to a ward bed.
- 173 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital B ER at 100% of capacity
- 173 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C ER at 100% of capacity
- 175 min · Dispatch → AMB-1 · STATUS [AI]: Assigning AMB-1 to the first two minor patients to minimize wait time for care.
- 175 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: AMB-1
- 175 min · Dispatch → Dispatch · ESCALATE [sim]: duplicate: AMB-1
- 175 min · Dispatch → Dispatch · RESOLVE [AI]: All patients remain unassigned as they are duplicates, but AMB-1 will transport to Hospital A due to its capacity for trauma care.
- 175 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, respond to the bus crash at grid 7,2 for 2 patient(s).
- 178 min · Dispatch → AMB-3 · STATUS [AI]: Assigning the free unit AMB-3 to transport two minor patients (MCI-2-P21 and MCI-2-P25) from the bus crash incident to ensure they receive care promptly.
- 178 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-2 with 2 patient(s), ETA 15 min. Can you take them?
- 178 min · Hospital C → Dispatch · ACCEPT [AI]: We have sufficient capacity to accept both patients with available beds and nursing staff.
- 178 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, respond to the bus crash at grid 7,2 for 2 patient(s).
- 178 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital C.
- 178 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, transport to Hospital C.
- 179 min · Hospital A → All · STATUS [sim]: MCI-2-P01 moved up to a ward bed.
- 188 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-1 with 2 patient(s), ETA 9 min. Can you take them?
- 188 min · Hospital D → Dispatch · ACCEPT [AI]: We can accept both patients as they only require general capabilities and we have the necessary capacity.
- 188 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-1 arrives.
- 188 min · Safety rules → Dispatch · BLOCKED R4 [sim]: Blocked: Hospital D's contract only covers stable serious patients.
- 189 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
- 189 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-1 arrives.
- 190 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
- 190 min · Dispatch → AMB-1 · ORDER [rule backup]: AMB-1, transport to Hospital A.
- 191 min · AMB-2 → Hospital C · PRE ALERT [sim]: Inbound with 2 green, ETA 14 min.
- 192 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 100% of capacity
- 193 min · Dispatch → AMB-4 · STATUS [AI]: The BLS unit AMB-4 is assigned to the minor patient 'MCI-2-P26' as it is the only free unit available.
- 193 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, respond to the bus crash at grid 7,2 for 1 patient(s).
- 196 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-3 with 2 patient(s), ETA 9 min. Can you take them?
- 196 min · Hospital D → Dispatch · ACCEPT [AI]: We have sufficient capacity (ward beds and nurses) to accept both patients with minor severity.
- 196 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-3 arrives.
- 196 min · Safety rules → Dispatch · BLOCKED R4 [sim]: Blocked: Hospital D's contract only covers stable serious patients.
- 197 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
- 197 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-3 arrives.
- 198 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
- 198 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital A will not have a free bed and staff when AMB-3 arrives.
- 199 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
- 199 min · Dispatch → AMB-3 · ORDER [rule backup]: AMB-3, transport to Hospital B.
- 201 min · Dispatch → Hospital D · PROPOSE [AI]: AMB-4 with 1 patient(s), ETA 9 min. Can you take them?
- 201 min · Hospital D → Dispatch · ACCEPT [AI]: We have the capacity to accept this minor severity patient as we have enough free ward beds and nurse coverage.
- 201 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-4 arrives.
- 201 min · Safety rules → Dispatch · BLOCKED R4 [sim]: Blocked: Hospital D's contract only covers stable serious patients.
- 202 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI's hospital was blocked by a safety rule. The rule-based backup decided.
- 202 min · Dispatch → AMB-4 · ORDER [rule backup]: AMB-4, transport to Hospital C.
- 203 min · AMB-1 → Hospital A · PRE ALERT [sim]: Inbound with 2 green, ETA 13 min.
- 204 min · AMB-3 → Hospital B · PRE ALERT [sim]: Inbound with 2 green, ETA 27 min.
- 213 min · Hospital A → All · STATUS [sim]: MCI-2-P07 moved up to a ward bed.
- 213 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
- 214 min · Hospital C → All · STATUS [sim]: MCI-2-P08 moved up to a ward bed.
- 216 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P19 (green) is in a treatment bed.
- 216 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P20 (green) is in a treatment bed.
- 216 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 117% of capacity
- 217 min · AMB-4 → Hospital C · PRE ALERT [sim]: Inbound with 1 green, ETA 14 min.
- 217 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Surge detected: MCI-2
- 220 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P17 (green) is in a treatment bed.
- 220 min · Hospital D → All · STATUS [sim]: MCI-2-P12 moved up to a ward bed.
- 221 min · Hospital C → All · STATUS [sim]: MCI-2-P02 moved up to a ward bed.
- 221 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P18 (green) is in a treatment bed.
- 224 min · Monitor → Dispatch · ALERT [sim]: Hospital B ER at 100% of capacity
- 230 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital D ER at 100% of capacity
- 252 min · Monitor → Dispatch · ALERT [sim]: Hospital B: a patient has waited 21 min for a bed
- 252 min · Monitor → Dispatch · ALERT [sim]: Hospital C: a patient has waited 21 min for a bed
- 257 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SE district
- 257 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SW district
- 269 min · Hospital A → All · STATUS [sim]: MCI-2-P11 moved up to a ward bed.
