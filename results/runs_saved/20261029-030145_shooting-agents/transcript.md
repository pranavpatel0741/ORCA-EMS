# Shooting · agents

Policy: agents · model: gpt-4o-mini · information: partial · seed 7 · 150 simulated minutes

## How well it went

| Measure | Value |
|---|---|
| Deaths | 0 |
| Critical patients in care within 60 min | 100% |
| Critical patients: call to definitive care (mean) | 40.5 min |
| Call to first ambulance on scene (mean) | 14 min |
| Ambulance minutes waiting at ER doors (beyond 10 min) | 13.0 min |
| Hospital minutes over capacity | 20 min |
| Calls with no ambulance after 30 min | 0 |
| Patients still not in care at the end | 0 |
| Proposals blocked by safety rules | 0 |
| Decisions sent for human review | 2 |
| Synthetic outcome score (higher is better) | 1.8 |
| AI calls | 9 |
| AI tokens | 13115 |
| Decisions by AI agents | 6 |
| Decisions by the rule backup | 0 |

## Negotiations


**AMB-1** · 1 patient(s) · MCI-1 → Hospital A (decided by agents)
-  29 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  29 min · Hospital C → Dispatch · COUNTER [AI]: I can accept MCI-1-P1 who can wait for a surgical bay while MCI-1-P0 would need immediate trauma bay access which is currently not available.
-  29 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  29 min · Hospital C → Dispatch · ACCEPT [AI]: We have sufficient capacity to accept this critical trauma patient, with available beds, a surgeon, and a trauma bay.
-  29 min · Dispatch → Human reviewer · ESCALATE [AI]: Confidence 0.61 for AMB-1 → Hospital C; asking for review.

**AMB-2** · 1 patient(s) · MCI-1 → Hospital C (decided by agents)
-  29 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-2 with 1 patient(s), ETA 9 min. Can you take them?
-  29 min · Hospital C → Dispatch · ACCEPT [AI]: We have a critical shortage of trauma bays, and MCI-1-P0 requires immediate access that we cannot provide. I can, however, accommodate MCI-1-P1.
-  29 min · Dispatch → Human reviewer · ESCALATE [AI]: Confidence 0.61 for AMB-2 → Hospital C; asking for review.

## Full conversation

-   0 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SW district
-   2 min · 911 caller → Dispatch · 911 CALL [sim]: “I heard gunshots, people are down, I'm hiding.” (shooting, about 2 hurt, grid 11,8)
-   2 min · Dispatch → Dispatch · PRIORITY REPORT [AI]: MCI: about 1 critical, 1 serious, 0 minor; urgency 1.0. The call indicates a shooting with people down, suggesting a high likelihood of critical injuries, thus warranting a maximum urgency level. Police are needed due to the violent situation, while no trapped victims require fire services.
-   2 min · Dispatch → AMB-1 · STATUS [AI]: AMB-1 is the closest free unit and will arrive at the MCI scene quickly to triage waiting patients.
-   2 min · Dispatch → AMB-2 · STATUS [AI]: AMB-2 is the second closest unit and will also respond to assist with the mass-casualty incident.
-   2 min · Dispatch → AMB-3 · STATUS [AI]: AMB-3 has a longer ETA but is still needed to cover for potential additional patients during triage.
-   2 min · Dispatch → AMB-4 · STATUS [AI]: AMB-4 will respond to ensure all potential patients are handled.
-   2 min · Dispatch → dispatch · PRIORITY REPORT [sim]: The call indicates a shooting with people down, suggesting a high likelihood of critical injuries, thus warranting a maximum urgency level. Police are needed due to the violent situation, while no trapped victims require fire services.
-   2 min · Safety rules → Dispatch · CAUTION [sim]: Scene is not secure. AMB-1 will stage nearby until police clear it.
-   2 min · Dispatch → AMB-1 · ORDER [AI]: AMB-1, respond to the shooting at grid 11,8 for patients, triage on arrival.
-   2 min · Safety rules → Dispatch · CAUTION [sim]: Scene is not secure. AMB-2 will stage nearby until police clear it.
-   2 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, respond to the shooting at grid 11,8 for patients, triage on arrival.
-   2 min · Safety rules → Dispatch · CAUTION [sim]: Scene is not secure. AMB-3 will stage nearby until police clear it.
-   2 min · Dispatch → AMB-3 · ORDER [AI]: AMB-3, respond to the shooting at grid 11,8 for patients, triage on arrival.
-   2 min · Safety rules → Dispatch · CAUTION [sim]: Scene is not secure. AMB-4 will stage nearby until police clear it.
-   2 min · Dispatch → AMB-4 · ORDER [AI]: AMB-4, respond to the shooting at grid 11,8 for patients, triage on arrival.
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the NE district
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the NW district
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SE district
-   2 min · Monitor → Dispatch · ALERT [sim]: Surge detected: MCI-1
-   7 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
-  15 min · Police → All units · SCENE SECURE [sim]: Scene is secure. Units can move in.
-  16 min · AMB-1 → Dispatch · SCENE REPORT [sim]: On scene. 2 patient(s): 2 red.
-  16 min · Dispatch → Dispatch · PRIORITY REPORT [AI]: MCI: about 2 critical, 1 serious, 0 minor; urgency 1.0. The caller reported gunshots with victims down, indicating a high urgency scenario. With 2 critical victims estimated, police are needed for safety and response.
-  16 min · Dispatch → dispatch · PRIORITY REPORT [sim]: The caller reported gunshots with victims down, indicating a high urgency scenario. With 2 critical victims estimated, police are needed for safety and response.
-  16 min · Dispatch → MedRide · MUTUAL AID REQUEST [sim]: request 2 mutual-aid unit(s)
-  16 min · MedRide → Dispatch · MUTUAL AID RESPONSE [sim]: accepted; 2 unit(s) ready at tick 26
-  16 min · Dispatch → MedRide · MUTUAL AID [AI]: Requesting 2 private ambulance(s).
-  26 min · MedRide → All · STATUS [sim]: units activated: PVT-1, PVT-2
-  26 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SE district
-  27 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
-  29 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  29 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-2 with 1 patient(s), ETA 9 min. Can you take them?
-  29 min · Hospital C → Dispatch · COUNTER [AI]: I can accept MCI-1-P1 who can wait for a surgical bay while MCI-1-P0 would need immediate trauma bay access which is currently not available.
-  29 min · Hospital C → Dispatch · ACCEPT [AI]: We have a critical shortage of trauma bays, and MCI-1-P0 requires immediate access that we cannot provide. I can, however, accommodate MCI-1-P1.
-  29 min · Dispatch → Hospital C · PROPOSE [AI]: AMB-1 with 1 patient(s), ETA 9 min. Can you take them?
-  29 min · Hospital C → Dispatch · ACCEPT [AI]: We have sufficient capacity to accept this critical trauma patient, with available beds, a surgeon, and a trauma bay.
-  29 min · Dispatch → Dispatch · ESCALATE [sim]: Confidence 0.61 for AMB-1 → Hospital C; asking for review.
-  29 min · Dispatch → Dispatch · ESCALATE [sim]: Confidence 0.61 for AMB-2 → Hospital C; asking for review.
-  29 min · Safety rules → Human reviewer · NEEDS APPROVAL [sim]: Waiting for review: AMB-1 to Hospital C. low confidence: the proposer asked for review. Alternative: AMB-1 to Hospital A.
-  29 min · Safety rules → Human reviewer · NEEDS APPROVAL [sim]: Waiting for review: AMB-2 to Hospital C. low confidence: the proposer asked for review. Alternative: AMB-2 to Hospital A.
-  31 min · Dispatch → AMB-1 · ORDER [rules]: AMB-1, transport to Hospital A.
-  31 min · Approval policy → Dispatch · OVERRIDDEN [sim]: Changed to: AMB-1 to Hospital A. a better option was available
-  31 min · Dispatch → AMB-2 · ORDER [AI]: AMB-2, transport to Hospital C.
-  31 min · Approval policy → Dispatch · APPROVED [sim]: Approved: AMB-2 to Hospital C. approved as proposed
-  34 min · AMB-2 → Hospital C · PRE ALERT [sim]: Inbound with 1 red, ETA 10 min.
-  35 min · AMB-1 → Hospital A · PRE ALERT [sim]: Inbound with 1 red, ETA 6 min.
-  35 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Surge detected: MCI-1
-  41 min · Hospital A → Dispatch · IN CARE [sim]: MCI-1-P0 (red) is in a treatment bed.
-  44 min · Hospital C → Dispatch · IN CARE [sim]: MCI-1-P1 (red) is in a treatment bed.
-  44 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the NE district
-  50 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the NW district
-  83 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SW district
-  97 min · Hospital A → All · STATUS [sim]: MCI-1-P0 moved up to a ward bed.
