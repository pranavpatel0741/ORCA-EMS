# School bus crash · rule_based

Policy: rule_based · model: none · information: partial · seed 7 · 270 simulated minutes

## How well it went

| Measure | Value |
|---|---|
| Deaths | 0 |
| Critical patients in care within 60 min | 50% |
| Critical patients: call to definitive care (mean) | 59 min |
| Call to first ambulance on scene (mean) | 5 min |
| Ambulance minutes waiting at ER doors (beyond 10 min) | 542.0 min |
| Hospital minutes over capacity | 689 min |
| Calls with no ambulance after 30 min | 0 |
| Patients still not in care at the end | 3 |
| Proposals blocked by safety rules | 4 |
| Decisions sent for human review | 0 |
| Synthetic outcome score (higher is better) | 28.3 |
| Agent calls (including scripted stand-ins) | 0 |
| Agent tokens (recorded usage) | 0 |
| Decisions by AI agents | 0 |
| Decisions by scripted stand-ins (not AI) | 0 |
| Decisions by the rule backup | 0 |

## Negotiations

No negotiations (baselines do not negotiate).

## Full conversation

-   0 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SW district
-   2 min · 911 caller → Dispatch · 911 CALL [sim]: “A bus flipped over! There are so many people, maybe 30 or so, people screaming.” (bus crash, about 31 hurt, grid 7,2)
-   2 min · Dispatch → AMB-1 · ORDER [rules]: AMB-1, respond to the bus crash at grid 7,2 for patients, triage on arrival.
-   2 min · Dispatch → AMB-2 · ORDER [rules]: AMB-2, respond to the bus crash at grid 7,2 for patients, triage on arrival.
-   2 min · Dispatch → AMB-3 · ORDER [rules]: AMB-3, respond to the bus crash at grid 7,2 for patients, triage on arrival.
-   2 min · Dispatch → AMB-4 · ORDER [rules]: AMB-4, respond to the bus crash at grid 7,2 for patients, triage on arrival.
-   2 min · Dispatch → MedRide · MUTUAL AID REQUEST [sim]: request 2 mutual-aid unit(s)
-   2 min · MedRide → Dispatch · MUTUAL AID RESPONSE [sim]: accepted; 2 unit(s) ready at tick 12
-   2 min · Dispatch → MedRide · MUTUAL AID [rules]: Requesting 2 private ambulance(s).
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the NE district
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the NW district
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SE district
-   2 min · Monitor → Dispatch · ALERT [sim]: Surge detected: MCI-2
-   7 min · AMB-1 → Dispatch · SCENE REPORT [sim]: On scene. 29 patient(s): 2 red, 11 yellow, 16 green.
-   7 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
-  12 min · MedRide → All · STATUS [sim]: units activated: PVT-1, PVT-2
-  12 min · Dispatch → PVT-1 · ORDER [rules]: PVT-1, respond to the bus crash at grid 7,2 for 1 patient(s), 1 critical.
-  12 min · Dispatch → PVT-2 · ORDER [rules]: PVT-2, respond to the bus crash at grid 7,2 for 1 patient(s), 1 critical.
-  17 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P15 from MCI-2 walked in without an ambulance.
-  17 min · Dispatch → PVT-2 · ORDER [rules]: PVT-2, transport to Hospital C.
-  18 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P15 (green) is in a treatment bed.
-  19 min · Dispatch → PVT-1 · ORDER [rules]: PVT-1, transport to Hospital A.
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
-  35 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P23 from MCI-2 walked in without an ambulance.
-  41 min · Dispatch → AMB-1 · ORDER [rules]: AMB-1, transport to Hospital C.
-  41 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-2 arrives.
-  41 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-3 arrives.
-  42 min · Dispatch → AMB-2 · ORDER [rules]: AMB-2, transport to Hospital B.
-  42 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital B will not have a free bed and staff when AMB-3 arrives.
-  43 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P13 from MCI-2 walked in without an ambulance.
-  43 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-3 arrives.
-  44 min · AMB-2 → Hospital B · PRE ALERT [sim]: Inbound with 2 yellow, ETA 24 min.
-  44 min · Dispatch → AMB-3 · ORDER [rules]: AMB-3, transport to Hospital A.
-  44 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital C.
-  44 min · Dispatch → AMB-4 · ORDER [rules]: AMB-4, transport to Hospital C.
-  44 min · Monitor → Dispatch · ALERT [sim]: Hospital D: a patient has waited 21 min for a bed
-  45 min · AMB-1 → Hospital C · PRE ALERT [sim]: Inbound with 2 yellow, ETA 13 min.
-  45 min · AMB-3 → Hospital A · PRE ALERT [sim]: Inbound with 2 yellow, ETA 15 min.
-  46 min · PVT-2 → Hospital C · PRE ALERT [sim]: Inbound with 1 red, ETA 12 min.
-  47 min · PVT-1 → Hospital A · PRE ALERT [sim]: Inbound with 1 red, ETA 17 min.
-  50 min · AMB-4 → Hospital C · PRE ALERT [sim]: Inbound with 2 yellow, ETA 16 min.
-  58 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P01 (red) is in a treatment bed.
-  58 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P02 (yellow) is in a treatment bed.
-  58 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P03 (yellow) is in a treatment bed.
-  58 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 100% of capacity
-  60 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P06 (yellow) is in a treatment bed.
-  60 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P07 (yellow) is in a treatment bed.
-  60 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
-  62 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P16 (green) is in a treatment bed.
-  64 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P00 (red) is in a treatment bed.
-  68 min · Hospital B → Dispatch · IN CARE [sim]: MCI-2-P04 (yellow) is in a treatment bed.
-  68 min · Hospital B → Dispatch · IN CARE [sim]: MCI-2-P05 (yellow) is in a treatment bed.
-  69 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P08 (yellow) is in a treatment bed.
-  74 min · Dispatch → AMB-1 · ORDER [rules]: AMB-1, respond to the bus crash at grid 7,2 for 2 patient(s).
-  77 min · Dispatch → AMB-3 · ORDER [rules]: AMB-3, respond to the bus crash at grid 7,2 for 2 patient(s).
-  79 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P27 (green) is in a treatment bed.
-  81 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
-  82 min · Dispatch → AMB-2 · ORDER [rules]: AMB-2, respond to the bus crash at grid 7,2 for 2 patient(s).
-  82 min · Monitor → Dispatch · ALERT [sim]: Hospital B ER at 100% of capacity
-  87 min · Monitor → Dispatch · ALERT [sim]: Hospital C: a patient has waited 21 min for a bed
-  91 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital D.
-  91 min · Dispatch → AMB-1 · ORDER [rules]: AMB-1, transport to Hospital D.
-  94 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P14 (green) is in a treatment bed.
-  95 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P22 (green) is in a treatment bed.
-  96 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital C.
-  96 min · Dispatch → AMB-3 · ORDER [rules]: AMB-3, transport to Hospital C.
-  99 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital C.
-  99 min · Dispatch → AMB-2 · ORDER [rules]: AMB-2, transport to Hospital C.
- 103 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
- 106 min · AMB-1 → Hospital D · PRE ALERT [sim]: Inbound with 2 yellow, ETA 10 min.
- 106 min · AMB-3 → Hospital C · PRE ALERT [sim]: Inbound with 1 yellow, 1 green, ETA 12 min.
- 111 min · AMB-2 → Hospital C · PRE ALERT [sim]: Inbound with 2 green, ETA 15 min.
- 117 min · Hospital C → All · STATUS [sim]: MCI-2-P01 moved up to a ward bed.
- 119 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P09 (yellow) is in a treatment bed.
- 119 min · Dispatch → PVT-1 · ORDER [rules]: PVT-1, respond to the bus crash at grid 7,2 for 2 patient(s).
- 119 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C: a patient has waited 52 min for a bed
- 120 min · Hospital A → All · STATUS [sim]: MCI-2-P00 moved up to a ward bed.
- 123 min · Dispatch → PVT-2 · ORDER [rules]: PVT-2, respond to the bus crash at grid 7,2 for 2 patient(s).
- 131 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P10 (yellow) is in a treatment bed.
- 135 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital C.
- 135 min · Dispatch → PVT-1 · ORDER [rules]: PVT-1, transport to Hospital C.
- 139 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital C.
- 139 min · Dispatch → PVT-2 · ORDER [rules]: PVT-2, transport to Hospital C.
- 139 min · Monitor → Dispatch · ALERT [sim]: Hospital C: a patient has waited 21 min for a bed
- 146 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P11 (yellow) is in a treatment bed.
- 148 min · PVT-1 → Hospital C · PRE ALERT [sim]: Inbound with 2 green, ETA 13 min.
- 150 min · PVT-2 → Hospital C · PRE ALERT [sim]: Inbound with 2 green, ETA 17 min.
- 150 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Surge detected: MCI-2
- 156 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the NE district
- 157 min · Hospital C → All · STATUS [sim]: MCI-2-P02 moved up to a ward bed.
- 157 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P12 (yellow) is in a treatment bed.
- 162 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P23 (green) is in a treatment bed.
- 165 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P13 (green) is in a treatment bed.
- 165 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital D: a patient has waited 121 min for a bed
- 170 min · Hospital A → All · STATUS [sim]: MCI-2-P06 moved up to a ward bed.
- 170 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
- 177 min · Hospital B → All · STATUS [sim]: MCI-2-P05 moved up to a ward bed.
- 179 min · Hospital B → All · STATUS [sim]: MCI-2-P04 moved up to a ward bed.
- 179 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital B ER at 100% of capacity
- 185 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SW district
- 209 min · Hospital C → All · STATUS [sim]: MCI-2-P09 moved up to a ward bed.
- 209 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P17 (green) is in a treatment bed.
- 213 min · Hospital A → All · STATUS [sim]: MCI-2-P07 moved up to a ward bed.
- 219 min · Hospital C → All · STATUS [sim]: MCI-2-P08 moved up to a ward bed.
- 219 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P18 (green) is in a treatment bed.
- 220 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P19 (green) is in a treatment bed.
- 224 min · Monitor → Dispatch · ALERT [sim]: Hospital B ER at 100% of capacity
- 229 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SE district
- 232 min · Hospital C → All · STATUS [sim]: MCI-2-P03 is boarding in the ER: no ward bed free.
- 244 min · Hospital D → All · STATUS [sim]: MCI-2-P11 moved up to a ward bed.
- 246 min · Hospital C → All · STATUS [sim]: MCI-2-P12 is boarding in the ER: no ward bed free.
- 246 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital D ER at 100% of capacity
- 259 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the NW district
- 266 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P20 (green) is in a treatment bed.
