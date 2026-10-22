# Assumptions

ORCA-EMS is a simulation study. Patients, capacities, and outcomes are synthetic. This file
lists every number that is not measured directly, so it can be checked before submission.

## Source ratios (provided by the project owner)

| Figure | Value | Source |
|---|---|---|
| Staffed community-hospital beds | 2.28 per 1,000 residents | AHA via KFF State Health Facts, 2024 |
| Direct-patient-care physicians | 2.55 per 1,000 | AAMC, 2024 |
| Practicing nurses | 12.4 per 1,000 | OECD Health at a Glance 2025 |

These are national population ratios, not resources located inside one town.

## Modeling assumptions (`sim/town.py`)

| Assumption | Value | Used for |
|---|---|---|
| EMS calls per resident per year | 0.13 | normal-day call rate |
| Daytime peak factor | 1.4 | call rate during the 3-hour window |
| ER treatment spaces | 0.45 per 1,000 | ER beds |
| Ward / ER bed split A/B/C/D | 40/25/20/15 % and 30/26/26/18 % | per-hospital beds |
| Hospital-based share of physicians and nurses | 60 % | on-duty staff |
| Staff per 24/7 post (shift factor) | 4.2 | on-duty staff |
| Surgeons among physicians | 6 % | trauma surgical teams on duty |
| ED nurses on duty | hospital nurses on duty × ER share of beds | nurse slots |
| ED nurse ratio | 1:4 (critical 1:2) | nurse slots per nurse |
| Staffed beds per operating room | 25 | ORs |
| ER spaces per trauma/resuscitation bay | 8 | trauma bays |
| One station covers | 105 km² (≈10-min drive at 45 km/h) | city ambulances (coverage-based) |
| Residents per ambulance | 20,000 | city ambulances (population-based) |
| Starting occupancy | ER 50–80 %, ward 65–80 % | hospital pressure at start |
| Inpatient stay | 2–7 days | ward turnover |
| Minimums | ≥ 4 ER beds per hospital, ≥ 1 surgical team at A and C, ≥ 2 private units | small towns stay workable |

Derived values for the default town (50,000 people, 20 × 20 km):
- about 1 call per 58 minutes
- 114 ward beds and 22 ER beds
- 2 surgical teams
- about 18 physicians and 89 hospital nurses on duty
- 4 city ambulances and 2 private ambulances

## Other simulation assumptions

- **Fictional town.** A 20 × 20 km square at Boston's latitude, so distances in km are realistic.
- **Travel.** Straight-line distance × 1.3 road factor, at 45 km/h emergency and 35 km/h returning, with lognormal noise.
- **Mass-casualty events.** A shooting (2 critical victims) and a bus crash (28–34 victims, simplified START triage mix). They are event-sized, not scaled with population.
- **Walk-ins.** 50–60 % of minor mass-casualty victims walk to the nearest hospital 15–45 minutes later.
- **Outcome model.** Synthetic logistic survival decay with time to definitive care. It is **not clinically validated**.
- **Offload.** The crew stays with its patients until the hospital takes them into care, with no cap.
- **Hospital D** takes ambulance patients only under its surge contract during an active surge.
- **Hospital B's stabilization bay** counts as definitive care for survival, but is excluded from the critical on-time rate.
- **Approval policy** for experiments (planned, M7): picks the better option on observed state after a 2-minute delay. Baselines use the same path.
