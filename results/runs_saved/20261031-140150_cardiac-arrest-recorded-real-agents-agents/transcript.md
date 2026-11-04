# Cardiac arrest recorded real agents · agents

Policy: agents · model: gpt-4o-mini · information: complete · seed 7 · 120 simulated minutes

## How well it went

| Measure | Value |
|---|---|
| Deaths | 0 |
| Critical patients in care within 60 min | 100% |
| Critical patients: call to definitive care (mean) | 40 min |
| Call to first ambulance on scene (mean) | 7 min |
| Ambulance minutes waiting at ER doors (beyond 10 min) | 0.0 min |
| Hospital minutes over capacity | 25 min |
| Calls with no ambulance after 30 min | 0 |
| Patients still not in care at the end | 0 |
| Proposals blocked by safety rules | 0 |
| Decisions sent for human review | 0 |
| Synthetic outcome score (higher is better) | 0.9 |
| AI calls | 5 |
| AI tokens | 6651 |
| Decisions by AI agents | 2 |
| Decisions by the rule backup | 0 |

## Negotiations


**AMB-1** · 1 patient(s) · I-CARDIAC → Hospital C (decided by agents)
-   9 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 19 min. Can you take them?
-   9 min · Hospital C → Dispatch · ACCEPT [AI]: We have the necessary capabilities and capacity to accept the patient in critical condition.

## Full conversation

-   0 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SW district
-   2 min · 911 caller → Dispatch · 911 CALL [sim]: “Someone's having chest pain, they can barely breathe.” (medical cardiac, about 1 hurt, grid 4,3)
-   2 min · Assessment → Dispatch · PRIORITY REPORT [AI]: SINGLE: about 1 critical, 0 serious, 0 minor; urgency 0.8. The caller reports chest pain and difficulty breathing, indicating a high urgency situation consistent with cardiac issues.
-   2 min · Dispatch → AMB-1 · STATUS [AI]: AMB-1 is the closest available unit, and the critical patient requires immediate transport for cardiac intervention.
-   2 min · Assessment → dispatch · PRIORITY REPORT [sim]: The caller reports chest pain and difficulty breathing, indicating a high urgency situation consistent with cardiac issues.
-   2 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, respond to the medical cardiac at grid 4,3 for 1 patient(s), 1 critical.
-   7 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
-   9 min · AMB-1 → Dispatch · SCENE REPORT [sim]: On scene. 1 patient(s): 1 red.
-   9 min · Assessment → Dispatch · PRIORITY REPORT [AI]: SINGLE: about 1 critical, 0 serious, 0 minor; urgency 1.0. The caller reports severe chest pain and difficulty breathing, indicating a critical condition that requires immediate medical intervention.
-   9 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 19 min. Can you take them?
-   9 min · Hospital C → Dispatch · ACCEPT [AI]: We have the necessary capabilities and capacity to accept the patient in critical condition.
-   9 min · Assessment → dispatch · PRIORITY REPORT [sim]: The caller reports severe chest pain and difficulty breathing, indicating a critical condition that requires immediate medical intervention.
-   9 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, transport to Hospital C.
-  27 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
-  28 min · AMB-1 → Hospital C · PRE ALERT [sim]: Inbound with 1 red, ETA 14 min.
-  42 min · Hospital C → Dispatch · IN CARE [sim]: I-CARDIAC-P0 (red) is in a treatment bed.
-  64 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 100% of capacity
-  69 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C ER at 100% of capacity
-  76 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SW district
