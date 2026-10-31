# Shooting · agents

Policy: agents · model: gpt-4o-mini · information: complete · seed 7 · 150 simulated minutes

## How well it went

| Measure | Value |
|---|---|
| Deaths | 0 |
| Critical patients in care within 60 min | 100% |
| Critical patients: call to definitive care (mean) | 40 min |
| Call to first ambulance on scene (mean) | 14 min |
| Ambulance minutes waiting at ER doors (beyond 10 min) | 13.0 min |
| Hospital minutes over capacity | 20 min |
| Calls with no ambulance after 30 min | 0 |
| Patients still not in care at the end | 0 |
| Proposals blocked by safety rules | 1 |
| Decisions sent for human review | 0 |
| Synthetic outcome score (higher is better) | 1.8 |
| AI calls | 6 |
| AI tokens | 9259 |
| Decisions by AI agents | 4 |
| Decisions by the rule backup | 1 |

## Negotiations


**AMB-2** · 1 patient(s) · MCI-1 → Hospital C (decided by agents)
-  17 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-2 with 1 patient(s), ETA 9 min. Can you take them?
-  17 min · Hospital C → Dispatch · ACCEPT [AI]: We have the necessary resources available to accept this critical patient, including a trauma bay, a surgeon, and enough nursing staff.

## Full conversation

-   0 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SW district
-   2 min · 911 caller → Dispatch · 911 CALL [sim]: “I heard gunshots, people are down, I'm hiding.” (shooting, about 2 hurt, grid 11,8)
-   2 min · Assessment → Dispatch · PRIORITY REPORT [AI]: MCI: about 1 critical, 1 serious, 0 minor; urgency 1.0. The call indicates a shooting with people down, suggesting a high likelihood of critical injuries, thus warranting a maximum urgency level. Police are needed due to the violent situation, while no trapped victims require fire services.
-   2 min · Dispatch → AMB-1 · STATUS [AI]: Assigned to the critical patient who requires trauma care.
-   2 min · Dispatch → AMB-2 · STATUS [AI]: Assigned to another critical patient needing immediate trauma attention.
-   2 min · Assessment → dispatch · PRIORITY REPORT [sim]: The call indicates a shooting with people down, suggesting a high likelihood of critical injuries, thus warranting a maximum urgency level. Police are needed due to the violent situation, while no trapped victims require fire services.
-   2 min · Safety rules → Dispatch · CAUTION [sim]: Scene is not secure. AMB-1 will stage nearby until police clear it.
-   2 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, respond to the shooting at grid 11,8 for 1 patient(s), 1 critical.
-   2 min · Safety rules → Dispatch · CAUTION [sim]: Scene is not secure. AMB-2 will stage nearby until police clear it.
-   2 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, respond to the shooting at grid 11,8 for 1 patient(s), 1 critical.
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SE district
-   2 min · Monitor → Dispatch · ALERT [sim]: Surge detected: MCI-1
-   7 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
-  15 min · Police → All units · SCENE SECURE [sim]: Scene is secure. Units can move in.
-  16 min · AMB-1 → Dispatch · SCENE REPORT [sim]: On scene. 2 patient(s): 2 red.
-  16 min · Assessment → Dispatch · PRIORITY REPORT [AI]: MCI: about 2 critical, 1 serious, 0 minor; urgency 1.0. The caller reported gunshots with victims down, indicating a high urgency scenario. With 2 critical victims estimated, police are needed for safety and response.
-  16 min · Assessment → dispatch · PRIORITY REPORT [sim]: The caller reported gunshots with victims down, indicating a high urgency scenario. With 2 critical victims estimated, police are needed for safety and response.
-  16 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI gave no usable hospital for this ambulance. The rule-based backup decided.
-  16 min · Rule backup → Dispatch · AI NOT USED [rule backup]: The AI gave no usable hospital for this ambulance. The rule-based backup decided.
-  16 min · Dispatch → AMB-1 · ORDER [rule backup]: AMB-1, transport to Hospital A.
-  16 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital A will not have a free bed and staff when AMB-2 arrives.
-  17 min · Dispatch → AMB-4 · STATUS [AI]: Free unit available to wait for other patients.
-  17 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-2 with 1 patient(s), ETA 9 min. Can you take them?
-  17 min · Hospital C → Dispatch · ACCEPT [AI]: We have the necessary resources available to accept this critical patient, including a trauma bay, a surgeon, and enough nursing staff.
-  17 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, respond to the shooting at grid 11,8 for patients, triage on arrival.
-  17 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, transport to Hospital C.
-  17 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the NE district
-  27 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
-  35 min · AMB-1 → Hospital A · PRE ALERT [sim]: Inbound with 1 red, ETA 4 min.
-  35 min · AMB-2 → Hospital C · PRE ALERT [sim]: Inbound with 1 red, ETA 10 min.
-  39 min · Hospital A → Dispatch · IN CARE [sim]: MCI-1-P0 (red) is in a treatment bed.
-  44 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Surge detected: MCI-1
-  45 min · Hospital C → Dispatch · IN CARE [sim]: MCI-1-P1 (red) is in a treatment bed.
-  59 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the NE district
-  62 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SE district
-  86 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SW district
-  95 min · Hospital A → All · STATUS [sim]: MCI-1-P0 moved up to a ward bed.
