# ORCA-EMS: When does agent negotiation help emergency coordination?

*Course report. Results tables are generated in `results/summary.md` from the recorded
5-seed grid (gpt-4o-mini).*

## 1. Problem

Ambulances are commonly taken to the nearest emergency department regardless of crowding. A
crowded ER causes **offload delay**: the crew waits with the patient until a bed is free, and
the ambulance is out of service. Crowding is driven largely by **boarding**: admitted patients
stay in ER beds because the wards are full. In a mass-casualty incident (MCI) the nearest
hospital floods while others still have capacity. Shared hospital status boards exist, but
they are self-reported, refreshed infrequently, and cannot negotiate.

**Question.** When does negotiation between AI agents improve emergency resource
coordination, and when are deterministic rules sufficient?

- **H1.** Negotiation reduces unresolved conflicts and capacity-related failures.
- **H2.** Negotiation improves time to definitive care for critical patients under scarcity.
- **H3.** The benefit is larger under surge demand and partial information.

## 2. Related work

- **Hospital status boards.** Systems such as EMResource share bed availability and diversion
  status across a region. EMTrack-style tools track MCI patients by triage color and destination.
  These systems display information; they do not negotiate.
- **Dispatch software (CAD).** It manages incident queues, unit status and maps.
- **Multi-agent task allocation.** The Contract Net Protocol (Smith, 1980) defines announce,
  bid and award. ORCA-EMS adapts it as propose / accept / counter / resolve between a dispatch
  agent and hospital agents.

## 3. Design

- **Town.** A fictional 20 × 20 km town of 50,000. Resources come from U.S. per-capita ratios:
  - 114 ward beds, 22 ER beds and 2 trauma surgical teams
  - 4 hospitals: a Level-1-style trauma center, a community hospital with a stabilization
    bay, a Level-2-style trauma center, and a private hospital with a surge contract
  - 4 city ambulances, plus 2 private units available through mutual aid
- **Engine.** A deterministic 1-minute tick loop with hidden ground truth.
  - **Patients:** severity, needs, and synthetic survival decay with time to care.
  - **Hospital flow:** ER queue, then trauma bay and OR, then ward. Boarders hold their ER bed.
  - **Ambulance cycle:** en route, staging at violent scenes, on scene, loading, transport,
    offload (the crew stays until the patient is admitted), handover, return.
- **Observations.**
  - Complete setting: live capacity, and victims known at the call.
  - Partial setting: a status board refreshed every 15 minutes, victims known only after the
    first unit's scene report, and walk-ins visible at the next board update.
- **Validator (R1–R9).** Every proposal is checked against true state. Examples: a critical
  patient rides alone; critical trauma goes to a trauma center; no entry to unsecured violent
  scenes; private contracts; nurse coverage; agents cannot change capacity. R6 sends risky
  decisions to approval, for baselines and agents alike.
- **Agents** (OpenAI Agents SDK, typed outputs, read-only tools, cached responses):
  - Assessment produces a priority report.
  - Dispatch assigns units and proposes hospitals.
  - Hospital agents A–D accept, reject or counter, and may request nurses from each other.
  - The Allocator resolves conflicts.
  
  A plain-Python orchestrator runs up to 3 negotiation rounds. A confidence gate
  (consistency, margin, freshness, validator-clean) decides between execute, information
  round, and human review. Failures fall back to the rule-based policy.
- **Baselines.**
  - *Nearest:* the nearest unit and nearest capable hospital, ignoring load.
  - *Rule-based:* a severity priority queue, capacity-aware routing with spreading, contract
    awareness, and mutual aid.
  
  Both use the same observations and ETA model as the agents.

## 4. Experiment

- **Grid:** 4 policies × {complete, partial} × {normal, surge} × 5 seeds.
- **Paired design:** each seed fixes the calls, patients and hospital load. Separate random
  streams keep a policy's choices from shifting background randomness.
- **Surge scenario:** the normal day's calls plus a shooting at minute 30 and a 28–34-victim
  bus crash at minute 35.
- **Metrics** (all from the event log):
  - response time and time to definitive care by severity
  - critical on-time rate (≤ 60 min)
  - hospital overload minutes and ambulance minutes at the ER beyond a 10-minute base
  - unserved calls and patients not in care at the end
  - deaths and the synthetic outcome score
  - rejections by rule, escalations and fallbacks
  - confidence calibration against a hindsight-best evaluator
  - LLM calls and tokens

## 5. Results

> **Historical results — audit correction (2026-10-31).** The tables below predate fixes to
> model-output grounding, staff-information access, and definitive-care metrics. Four stored
> records also differ from their associated logs. Do not present these tables as current-code
> results until the experiment grid is regenerated. See [the agent/evaluation audit](AGENT_EVAL_AUDIT.md).

**Baselines, 5 seeds.** Mean values for the surge scenario:

| | Deaths | Outcome score | Capacity failures | Response (min) | ER minutes over base |
|---|---|---|---|---|---|
| Nearest, complete info | 3.6 | 29 | 19 | 32 | 299 |
| Rule-based, complete info | 3.0 | 31 | 10 | 46 | 548 |
| Nearest, partial info | 3.8 | 29 | 20 | 25 | 288 |
| Rule-based, partial info | 3.6 | 30 | 9.8 | 48 | 536 |

The capacity-aware rule-based policy halves capacity-related failures and slightly improves
the synthetic outcome score. It pays for that in average response time and in ambulance
minutes waiting at ER doors, because it serves mass-casualty patients first and spreads
patients to hospitals that were farther away. On a normal day the two baselines perform almost
the same. This is the bar the agents must clear.

**Historical agents (gpt-4o-mini, 5 seeds, 40 agent-policy runs; 36 with model calls and 4 empty
scenarios).** Mean values; full tables with spreads are in
`results/summary.md`. Historical model answers are saved in `data/llm_cache/`. With the current
grounding and information-boundary fixes, 28 of the 40 agent-policy cells need new answers;
the old cache does not reproduce the entire grid with current code.

| | Critical on time | Critical: call to care (min) | Response (min) | ER minutes over base | Deaths |
|---|---|---|---|---|---|
| *Normal day, partial info* | | | | | |
| Nearest | 0% | 84 | 9.6 | 37 | 0 |
| Rule-based | 0% | 68 | 9.6 | 9.8 | 0 |
| Agents, no negotiation | 100% | 56 | 11 | 10 | 0 |
| Agents, negotiating | 100% | 56 | 11 | 10 | 0 |
| *Surge, partial info* | | | | | |
| Nearest | 37% | 63 | 25 | 288 | 3.8 |
| Rule-based | 37% | 63 | 48 | 536 | 3.6 |
| Agents, no negotiation | 36% | 69 | 60 | 533 | 3.4 |
| Agents, negotiating | 37% | 58 | 57 | 483 | 4.0 |
| *Surge, complete info* | | | | | |
| Nearest | 33% | 62 | 32 | 299 | 3.6 |
| Rule-based | 33% | 67 | 46 | 548 | 3.0 |
| Agents, no negotiation | 33% | 69 | 56 | 540 | 3.4 |
| Agents, negotiating | 33% | 69 | 54 | 538 | 3.0 |

Where the agents helped:
- **Incomplete information on a normal day.** Every critical patient reached care within 60
  minutes (both baselines: none), and 12–28 minutes sooner on average. The agents read the
  scene and hospital facts and avoided the hospitals that turned out to be full.
- **Negotiation under surge with partial information.** Compared with the same agents without
  negotiation, critical patients reached care 11 minutes sooner and ambulances waited less at
  ER doors (483 vs 533 minutes). Paired by seed, negotiation was better for critical care in
  6 of 10 surge runs and worse in 1.

Where they did not:
- **Response time in a surge.** The first ambulance reached calls later (54–60 minutes against
  25–48 for the baselines), because the agents commit units to mass-casualty patients first.
  Deaths and the outcome score are about the same as the baselines.
- **Complete information.** With an accurate status board, the agents add nothing over the
  rule-based policy.
- **Hypotheses.** H1 (fewer capacity failures with negotiation) is mixed. H2 (faster critical
  care in scarcity) is mixed, leaning positive. H3 (a larger benefit under surge and partial
  information) is not supported: the gain appears under partial information on a normal day,
  not under surge.

Cost: 64 LLM calls and about 135k tokens per negotiated run (88k without negotiation), around
2–3 US cents on gpt-4o-mini; the whole grid cost about $0.80. When an agent's answer was unusable, the
rule backup decided and the log and dashboard label it as such: 8% of decisions per negotiated
run on average (21% without negotiation, where a hospital's counter or rejection always goes to
the backup by design). Five seeds and one model make this descriptive evidence, not a significance
test.

## 6. Limitations

- Simulation only, with synthetic patients and capacities. The outcome model is not clinically
  validated.
- The resource ratios are national averages. The steps to on-duty staff are assumptions
  (ASSUMPTIONS.md).
- Travel uses straight-line distance × 1.3 at a fixed speed. There are no street networks and
  no live tracking.
- One town layout, 5 seeds, one small model: the evidence is descriptive.
- LLM behavior depends on the model and the prompts. Results replay exactly from the cache,
  but a different model may behave differently.

## 7. Future work

See `docs/FUTURE_WORK.md`: shadow-mode evaluation on real dispatch data, inter-hospital
transfers, street-network travel, and regional mutual aid.
