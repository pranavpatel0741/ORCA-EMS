# School bus crash · nearest

Policy: nearest · model: none · information: partial · seed 7 · 270 simulated minutes

## How well it went

| Measure | Value |
|---|---|
| Deaths | 0 |
| Critical patients in care within 60 min | 50% |
| Critical patients: call to definitive care (mean) | 58.5 min |
| Call to first ambulance on scene (mean) | 5 min |
| Ambulance minutes waiting at ER doors (beyond 10 min) | 221.0 min |
| Hospital minutes over capacity | 701 min |
| Calls with no ambulance after 30 min | 0 |
| Patients still not in care at the end | 0 |
| Proposals blocked by safety rules | 9 |
| Decisions sent for human review | 0 |
| Synthetic outcome score (higher is better) | 28.1 |
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
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the NE district
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the NW district
-   2 min · Monitor → Dispatch · ALERT [sim]: No free ambulance in the SE district
-   2 min · Monitor → Dispatch · ALERT [sim]: Surge detected: MCI-2
-   7 min · AMB-1 → Dispatch · SCENE REPORT [sim]: On scene. 29 patient(s): 2 red, 11 yellow, 16 green.
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
-  35 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P23 from MCI-2 walked in without an ambulance.
-  41 min · Dispatch → AMB-1 · ORDER [rules]: AMB-1, transport to Hospital C.
-  41 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-2 arrives.
-  41 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-3 arrives.
-  42 min · Dispatch → AMB-2 · ORDER [rules]: AMB-2, transport to Hospital A.
-  42 min · Dispatch → AMB-3 · ORDER [rules]: AMB-3, transport to Hospital C.
-  43 min · Hospital D → Dispatch · WALK-IN [sim]: MCI-2-P13 from MCI-2 walked in without an ambulance.
-  44 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-4 arrives.
-  44 min · Monitor → Dispatch · ALERT [sim]: Hospital D: a patient has waited 21 min for a bed
-  45 min · AMB-3 → Hospital C · PRE ALERT [sim]: Inbound with 2 yellow, ETA 15 min.
-  45 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-4 arrives.
-  46 min · AMB-2 → Hospital A · PRE ALERT [sim]: Inbound with 1 red, ETA 11 min.
-  46 min · Dispatch → AMB-4 · ORDER [rules]: AMB-4, transport to Hospital A.
-  47 min · AMB-1 → Hospital C · PRE ALERT [sim]: Inbound with 1 red, ETA 17 min.
-  47 min · AMB-4 → Hospital A · PRE ALERT [sim]: Inbound with 2 yellow, ETA 13 min.
-  57 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P01 (red) is in a treatment bed.
-  60 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P04 (yellow) is in a treatment bed.
-  60 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P05 (yellow) is in a treatment bed.
-  60 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P02 (yellow) is in a treatment bed.
-  60 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P03 (yellow) is in a treatment bed.
-  60 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
-  60 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 100% of capacity
-  62 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P16 (green) is in a treatment bed.
-  64 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P00 (red) is in a treatment bed.
-  73 min · Dispatch → AMB-2 · ORDER [rules]: AMB-2, respond to the bus crash at grid 7,2 for 2 patient(s).
-  74 min · Dispatch → AMB-4 · ORDER [rules]: AMB-4, respond to the bus crash at grid 7,2 for 2 patient(s).
-  76 min · Dispatch → AMB-3 · ORDER [rules]: AMB-3, respond to the bus crash at grid 7,2 for 2 patient(s).
-  79 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P27 (green) is in a treatment bed.
-  81 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
-  85 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital D will not have a free bed and staff when AMB-2 arrives.
-  86 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-2 arrives.
-  87 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital A will not have a free bed and staff when AMB-2 arrives.
-  88 min · Dispatch → AMB-2 · ORDER [rules]: AMB-2, transport to Hospital B.
-  91 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital D.
-  91 min · Dispatch → AMB-4 · ORDER [rules]: AMB-4, transport to Hospital D.
-  93 min · Safety rules → Dispatch · CAUTION [sim]: Every capable hospital is full. The patient will wait at Hospital D.
-  93 min · Dispatch → AMB-3 · ORDER [rules]: AMB-3, transport to Hospital D.
-  94 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P14 (green) is in a treatment bed.
-  95 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P22 (green) is in a treatment bed.
-  97 min · AMB-2 → Hospital B · PRE ALERT [sim]: Inbound with 2 yellow, ETA 18 min.
- 103 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
- 105 min · AMB-4 → Hospital D · PRE ALERT [sim]: Inbound with 2 yellow, ETA 11 min.
- 108 min · AMB-3 → Hospital D · PRE ALERT [sim]: Inbound with 2 yellow, ETA 9 min.
- 114 min · Dispatch → AMB-1 · ORDER [rules]: AMB-1, respond to the bus crash at grid 7,2 for 2 patient(s).
- 115 min · Hospital B → Dispatch · IN CARE [sim]: MCI-2-P06 (yellow) is in a treatment bed.
- 115 min · Hospital B → Dispatch · IN CARE [sim]: MCI-2-P07 (yellow) is in a treatment bed.
- 115 min · Monitor → Dispatch · ALERT [sim]: Hospital B ER at 100% of capacity
- 116 min · Hospital A → All · STATUS [sim]: MCI-2-P01 moved up to a ward bed.
- 119 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C ER at 100% of capacity
- 120 min · Hospital C → All · STATUS [sim]: MCI-2-P00 moved up to a ward bed.
- 131 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P08 (yellow) is in a treatment bed.
- 131 min · Dispatch → AMB-1 · ORDER [rules]: AMB-1, transport to Hospital C.
- 132 min · Dispatch → AMB-2 · ORDER [rules]: AMB-2, respond to the bus crash at grid 7,2 for 2 patient(s).
- 141 min · AMB-1 → Hospital C · PRE ALERT [sim]: Inbound with 1 yellow, 1 green, ETA 14 min.
- 146 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P09 (yellow) is in a treatment bed.
- 149 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 100% of capacity
- 152 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C ER at 100% of capacity
- 154 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-2 arrives.
- 155 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P12 (yellow) is in a treatment bed.
- 155 min · Dispatch → AMB-2 · ORDER [rules]: AMB-2, transport to Hospital A.
- 155 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 117% of capacity
- 159 min · Hospital C → All · STATUS [sim]: MCI-2-P02 moved up to a ward bed.
- 159 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P17 (green) is in a treatment bed.
- 162 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P10 (yellow) is in a treatment bed.
- 165 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P11 (yellow) is in a treatment bed.
- 166 min · AMB-2 → Hospital A · PRE ALERT [sim]: Inbound with 2 green, ETA 16 min.
- 169 min · Hospital A → All · STATUS [sim]: MCI-2-P05 moved up to a ward bed.
- 169 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
- 171 min · Hospital A → All · STATUS [sim]: MCI-2-P04 moved up to a ward bed.
- 173 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C ER at 100% of capacity
- 182 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P18 (green) is in a treatment bed.
- 182 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P19 (green) is in a treatment bed.
- 183 min · Dispatch → AMB-4 · ORDER [rules]: AMB-4, respond to the bus crash at grid 7,2 for 2 patient(s).
- 186 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 100% of capacity
- 192 min · Dispatch → AMB-3 · ORDER [rules]: AMB-3, respond to the bus crash at grid 7,2 for 2 patient(s).
- 192 min · Dispatch → AMB-4 · ORDER [rules]: AMB-4, transport to Hospital C.
- 192 min · Monitor → Dispatch · ALERT [sim]: Hospital C ER at 100% of capacity
- 200 min · Safety rules → Dispatch · BLOCKED R2 [sim]: Blocked: Hospital C will not have a free bed and staff when AMB-3 arrives.
- 201 min · Dispatch → AMB-3 · ORDER [rules]: AMB-3, transport to Hospital A.
- 205 min · AMB-4 → Hospital C · PRE ALERT [sim]: Inbound with 2 green, ETA 14 min.
- 206 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
- 211 min · AMB-3 → Hospital A · PRE ALERT [sim]: Inbound with 2 green, ETA 20 min.
- 211 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Surge detected: MCI-2
- 215 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SE district
- 220 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P20 (green) is in a treatment bed.
- 223 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the SW district
- 225 min · Hospital B → All · STATUS [sim]: MCI-2-P06 moved up to a ward bed.
- 231 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P25 (green) is in a treatment bed.
- 231 min · Monitor → Dispatch · ALERT [sim]: Hospital A ER at 117% of capacity
- 234 min · Hospital C → All · STATUS [sim]: MCI-2-P03 moved up to a ward bed.
- 234 min · Hospital C → Dispatch · IN CARE [sim]: MCI-2-P21 (green) is in a treatment bed.
- 236 min · Hospital D → All · STATUS [sim]: MCI-2-P09 moved up to a ward bed.
- 236 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P23 (green) is in a treatment bed.
- 243 min · Hospital A → Dispatch · IN CARE [sim]: MCI-2-P26 (green) is in a treatment bed.
- 244 min · Hospital C → All · STATUS [sim]: MCI-2-P12 moved up to a ward bed.
- 244 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital C ER at 100% of capacity
- 263 min · Hospital D → All · STATUS [sim]: MCI-2-P11 moved up to a ward bed.
- 263 min · Hospital D → Dispatch · IN CARE [sim]: MCI-2-P13 (green) is in a treatment bed.
- 263 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital D: a patient has waited 219 min for a bed
- 268 min · Hospital B → All · STATUS [sim]: MCI-2-P07 moved up to a ward bed.
- 268 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: Hospital A ER at 100% of capacity
- 270 min · Monitor → Dispatch · ALERT CLEARED [sim]: Cleared: No free ambulance in the NW district
