# Shooting · agents

Policy: agents · model: gpt-4o-mini · information: complete · seed 7 · 150 simulated minutes

## How well it went

| Measure | Value |
|---|---|
| Deaths | 0 |
| Critical patients in care within 60 min | 100% |
| Critical patients: call to definitive care (mean) | 39 min |
| Call to first ambulance on scene (mean) | 14 min |
| Ambulance minutes waiting at ER doors (beyond 10 min) | 13.0 min |
| Hospital minutes over capacity | 20 min |
| Calls with no ambulance after 30 min | 0 |
| Patients still not in care at the end | 0 |
| Proposals blocked by safety rules | 0 |
| Decisions sent for human review | 2 |
| Synthetic outcome score (higher is better) | 1.8 |
| AI calls | 7 |
| AI tokens | 11190 |
| Decisions by AI agents | 4 |
| Decisions by the rule backup | 0 |

## Negotiations


**AMB-1** · 1 patient(s) · MCI-1 → Hospital A (decided by agents)
-  16 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  16 min · Hospital C → Dispatch · COUNTER [AI]: I can accept MCI-1-P1, but will need to wait for a trauma bay to be available for MCI-1-P0 shortly after that.
-  16 min · Dispatch → Allocator · ESCALATE [AI]: route unresolved: AMB-1
-  16 min · Allocator → Dispatch · RESOLVE [AI]: AMB-1 is assigned to Hospital A, which can treat the critical trauma patient despite having no ER beds.
-  16 min · Dispatch → Hospital A · STATUS [AI]: Confidence 0.79; requesting your current status.
-  16 min · Dispatch → Human reviewer · ESCALATE [AI]: Confidence 0.79 for AMB-1 → Hospital A; asking for review.

**AMB-2** · 1 patient(s) · MCI-1 → Hospital C (decided by agents)
-  16 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-2 with 1 patient(s), ETA 9 min. Can you take them?
-  16 min · Hospital C → Dispatch · ACCEPT [AI]: I currently have a trauma bay occupied but expect to have it free soon after the arrival of MCI-1-P1.
-  16 min · Dispatch → Human reviewer · ESCALATE [AI]: Confidence 0.70 for AMB-2 → Hospital C; asking for review.

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
-  16 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  16 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-2 with 1 patient(s), ETA 9 min. Can you take them?
-  16 min · Hospital C → Dispatch · COUNTER [AI]: I can accept MCI-1-P1, but will need to wait for a trauma bay to be available for MCI-1-P0 shortly after that.
-  16 min · Hospital C → Dispatch · ACCEPT [AI]: I currently have a trauma bay occupied but expect to have it free soon after the arrival of MCI-1-P1.
-  16 min · Dispatch → Allocator · ESCALATE [sim]: route unresolved: AMB-1
-  16 min · Allocator → Dispatch · RESOLVE [AI]: AMB-1 is assigned to Hospital A, which can treat the critical trauma patient despite having no ER beds.
-  16 min · Dispatch → Hospital A · STATUS [AI]: Confidence 0.79; requesting your current status.
-  16 min · Dispatch → Dispatch · ESCALATE [sim]: Confidence 0.79 for AMB-1 → Hospital A; asking for review.
-  16 min · Dispatch → Dispatch · ESCALATE [sim]: Confidence 0.70 for AMB-2 → Hospital C; asking for review.
-  16 min · Assessment → dispatch · PRIORITY REPORT [sim]: The caller reported gunshots with victims down, indicating a high urgency scenario. With 2 critical victims estimated, police are needed for safety and response.
-  16 min · Safety rules → Human reviewer · NEEDS APPROVAL [sim]: Waiting for review: AMB-1 to Hospital A. low confidence: the proposer asked for review. Alternative: AMB-1 to Hospital C.
-  16 min · Safety rules → Human reviewer · NEEDS APPROVAL [sim]: Waiting for review: AMB-2 to Hospital C. low confidence: the proposer asked for review. Alternative: AMB-2 to Hospital A.
-  18 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, transport to Hospital A.
-  18 min · Approval policy → Dispatch · APPROVED [sim]: Approved: AMB-1 to Hospital A. approved as proposed
-  18 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, transport to Hospital C.
-  18 min · Approval policy → Dispatch · APPROVED [sim]: Approved: AMB-2 to Hospital C. approved as proposed
-  27 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
-  35 min · AMB-1 → Hospital A · PRE ALERT [sim]: Inbound with 1 red, ETA 6 min.
-  35 min · AMB-2 → Hospital C · PRE ALERT [sim]: Inbound with 1 red, ETA 6 min.
-  35 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Surge detected: MCI-1
-  41 min · Hospital A → Dispatch · IN CARE [sim]: MCI-1-P0 (red) is in a treatment bed.
-  41 min · Hospital C → Dispatch · IN CARE [sim]: MCI-1-P1 (red) is in a treatment bed.
-  58 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SE district
-  86 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SW district
-  97 min · Hospital A → All · STATUS [sim]: MCI-1-P0 moved up to a ward bed.
