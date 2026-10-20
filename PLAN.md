# EMERGE-AI: End-to-End Build Plan

**Project:** Multi-agent emergency response coordination simulator (course mid-term)
**Owner:** Pranav Patel
**Deadline:** November 4, 2026, 18:00 (submission: text box with repo link and results summary)
**Required by the assignment:** Python, OpenAI Agents SDK, at least four distinct agents, structured messages, negotiation, reproducible synthetic data, an interactive visualization, and *measurable* evidence that coordination improves outcomes.

This file is the single source of truth for the build. Read it fully before writing code. Work milestone by milestone (Section 15), and do not start a milestone until the previous one passes its acceptance check.

---

## 1. Problem and research question

**Real-world problem.** In practice, ambulances are often sent to the nearest emergency department regardless of how crowded it is. Crowded ERs cause *offload delays*: crews wait in the hallway to hand over patients, and their ambulance can't answer the next call. During mass-casualty events (e.g., a bus crash), sending everyone to the nearest hospital overloads it while other capable hospitals still have capacity. Shared hospital status boards exist today, but they are self-reported, updated infrequently, and cannot negotiate.

**What we build.** A reproducible simulation of a city EMS system in which hospital, dispatch, assessment, and allocation agents share status and negotiate where each patient goes, under hard safety rules and human approval for high-risk decisions.

**Research question.** *When does negotiation between AI agents improve emergency resource coordination, and when are deterministic rules sufficient?*

**Hypotheses (to test, not assume):**
- H1: Negotiation reduces unresolved resource conflicts and capacity-related failures.
- H2: Negotiation improves time to definitive care for critical patients during resource scarcity.
- H3: The benefit is larger under surge demand and under partial information than under normal demand or complete information.

---

## 2. Scope

### In scope
- Normal-day demand (single-patient calls) and surge demand (bus crash, shooting), in one system.
- Public and private hospitals; city and private ambulances; police and fire teams.
- Hidden ground truth vs. agent observations (complete vs. partial-and-changing information).
- Four LLM agent types (seven instances), negotiation, confidence-based escalation, human approval.
- Deterministic engine, validator, monitor, baselines, metrics, experiments.
- Streamlit dashboard with a live Boston map, replay mode, and live mode.

### Out of scope (future work; do not build)
- Training ML models, embeddings, retrieval, demand forecasting.
- Real-time external data feeds (news, traffic, social media), Google Maps APIs.
- Crime prediction or a police dispatch system.
- Real hospital data integration or any claim of clinical validity.

**Scope is frozen.** If something seems missing, add it to `docs/FUTURE_WORK.md` instead of building it.

---

## 3. Core design principles

1. **The engine is the only source of truth.** Agents propose; the engine validates and commits. Agents never mutate state directly.
2. **Hidden truth vs. observations.** The engine knows true severity, true counts, and true capacity. Agents only receive observations from `sim/observations.py`.
3. **Hard rules beat AI.** The validator enforces safety, eligibility, and contracts. No agent can override it.
4. **Determinism and reproducibility.** Every random draw uses a seeded `numpy.random.Generator`. LLM responses are cached so a run can be replayed exactly.
5. **Simulated time is not wall-clock time.** The engine waits for agent decisions before completing a tick. A slow API call never delays a virtual ambulance.
6. **Event-driven AI.** Agents run only when a decision is needed, never on every tick.
7. **Fair comparison.** Baselines receive the same observations and ETA estimates as the agents.
8. **Honest outcomes.** Results are computed by the engine, never scripted. Outcome scores are labeled as synthetic models.

---

## 4. Tech stack

Python 3.11. Pin versions in `requirements.txt`:

```
openai-agents==0.24.0
pydantic>=2.7,<3
numpy>=1.26
pandas>=2.2
duckdb>=1.0
streamlit>=1.38
plotly>=5.24
pydeck>=0.9
faker>=26
python-dotenv>=1.0
pytest>=8
ruff>=0.6
```

**Important:** the OpenAI Agents SDK changes frequently. Before writing agent code, check the installed version's API (`Agent`, `Runner.run`, `@function_tool`, `agent.as_tool`, `output_type`, `ModelSettings`, `RunHooks`, tracing configuration) against its documentation or source, and adapt. Do not guess APIs.

Configuration lives in `.env` (never committed) and `config/settings.py`:

```
OPENAI_API_KEY=...
OPENAI_MODEL=...          # a small, inexpensive model; set by the owner
LLM_MODE=live             # live | cache_only | record
APPROVAL_MODE=policy      # policy (experiments) | interactive (demo)
```

---

## 5. Repository structure

```
emerge-ai/
├── PLAN.md                     # this file
├── CLAUDE.md                   # short pointer: "Follow PLAN.md; update PROGRESS.md"
├── PROGRESS.md                 # milestone checklist, updated as work completes
├── README.md
├── ASSUMPTIONS.md
├── ATTRIBUTION.md
├── requirements.txt
├── .env.example
├── run.py                      # CLI: run one scenario with one policy
├── config/
│   └── settings.py
├── sim/
│   ├── entities.py             # Pydantic models and enums
│   ├── state_machine.py        # ambulance, patient, scene, team transitions
│   ├── engine.py               # tick loop, commit API
│   ├── hospital.py             # capacity accounting, treatment, staff loans
│   ├── observations.py         # complete vs partial views
│   ├── validator.py            # hard rules R1–R9
│   ├── travel.py               # distance, ETA, calibration hooks
│   ├── outcomes.py             # synthetic outcome model
│   ├── generator.py            # seeded scenarios
│   ├── calibrate.py            # SF EMS data → calibration.json
│   ├── monitor.py              # deterministic threshold alerts
│   └── events.py               # event types and JSONL logger
├── protocol/
│   ├── messages.py             # Message schema, message types
│   └── negotiation.py          # negotiation state machine
├── agents/
│   ├── models.py               # Pydantic output types for agents
│   ├── tools.py                # read-only function tools
│   ├── prompts/                # one instructions file per agent
│   ├── assessment.py
│   ├── dispatch.py
│   ├── hospital_agent.py
│   ├── allocator.py
│   ├── orchestrator.py         # event triggers, decision cycles
│   ├── confidence.py           # confidence score and gate
│   ├── approval.py             # policy vs interactive approval
│   ├── narratives.py           # LLM caller narratives (cached)
│   └── llm_cache.py            # record / replay of LLM responses
├── baselines/
│   ├── nearest.py
│   └── rule_based.py
├── eval/
│   ├── metrics.py
│   ├── run_experiments.py
│   └── report_tables.py
├── app/
│   ├── streamlit_app.py
│   ├── map_view.py             # pydeck (primary), Plotly (fallback)
│   └── panels.py
├── data/
│   ├── raw/                    # downloaded SF EMS sample (gitignored if large)
│   ├── calibration.json
│   ├── routes.json             # optional precomputed street routes
│   ├── scenarios/              # seed_XX_<demand>.json
│   └── llm_cache/
├── logs/                       # run_<id>.jsonl
├── results/                    # experiment outputs
├── docs/
│   └── FUTURE_WORK.md
└── tests/
```

---

## 6. Domain model (`sim/entities.py`)

All models are Pydantic v2. IDs are strings. Time is an integer tick (1 tick = 1 simulated minute). Locations are `(lat, lon)`.

### Enums
- `Severity`: `CRITICAL`, `SERIOUS`, `MINOR`, `EXPECTANT`
- `IncidentType`: `MEDICAL_CARDIAC`, `MEDICAL_STROKE`, `MEDICAL_GENERAL`, `FALL`, `VEHICLE_CRASH`, `BUS_CRASH`, `SHOOTING`
- `Capability`: `TRAUMA_L1`, `TRAUMA_L2`, `CARDIAC_CATH`, `STROKE`, `GENERAL`
- `Owner`: `PUBLIC`, `PRIVATE`
- `UnitType`: `ALS`, `BLS`
- `AmbulanceState`: see Section 7
- `TeamKind`: `POLICE`, `FIRE`
- `Mode`: `SINGLE`, `MCI`

### Hospital
`id, name, location, owner, capabilities: set[Capability], er_beds_total, trauma_bays_total, ors_total, trauma_surgeons_total, nurses_total, min_nurse_coverage, surge_contract: SurgeContract | None`, plus live counters held by `sim/hospital.py` (occupied beds, bays, ORs, busy surgeons, busy nurses, patients queued, ambulances waiting).

`SurgeContract` (private hospitals): `max_surge_patients: int, eligible_severities: set[Severity], accepts_critical_trauma: bool`.

### Ambulance
`id, owner, unit_type, home_station, location, state, state_until_tick, capacity (1 critical or 2 non-critical), assigned_incident, onboard_patient_ids, destination_hospital`.

Private ambulances belong to a `PrivateFirm`: `id, unit_ids, max_mutual_aid_units, activation_minutes`.

### Patient
`id, incident_id, true_severity (hidden), observed_severity (None until assessed on scene), needs: PatientNeeds, deterioration_rate, status (WAITING_ON_SCENE, IN_TRANSPORT, WAITING_AT_ER, IN_TREATMENT, DISCHARGED, DECEASED), timestamps (call, unit_on_scene, loaded, arrived_hospital, definitive_care_start)`.

`PatientNeeds`: `trauma_bay: bool, trauma_surgeon: bool, or_within_minutes: int | None, er_bed: bool, nurse: bool, capability: Capability | None`.

### Incident
`id, type, location, call_tick, reported_victims (from the call), true_victim_ids (hidden), violent: bool, scene_secured: bool, scene_secured_tick (hidden, drawn by generator), needs_fire_extrication: bool, narrative: str`.

### ResponderTeam
`id, kind, location, state (IDLE, EN_ROUTE, ON_SCENE, RETURNING), assigned_incident`.

---

## 7. State machines (`sim/state_machine.py`)

### Ambulance
```
IDLE → EN_ROUTE → [STAGING if violent and unsecured] → ON_SCENE → LOADING
     → TRANSPORTING → WAITING_AT_ER → HANDOVER → RETURNING → IDLE
```
- `EN_ROUTE`, `TRANSPORTING`, `RETURNING`: duration = travel time (Section 9).
- `STAGING`: hold at a point ~0.5 km from the scene until `scene_secured` becomes true. Rule R5.
- `ON_SCENE`: assessment time, sampled (default 8–15 min for critical, 5–10 otherwise).
- `LOADING`: 3–6 min.
- `WAITING_AT_ER`: depends on ER crowding (Section 9). This is where offload delay is measured.
- `HANDOVER`: 5–10 min.
- A unit may be reassigned while `IDLE`, `RETURNING`, or `EN_ROUTE`/`STAGING` (empty only). Never while carrying patients.

### Patient
```
WAITING_ON_SCENE → IN_TRANSPORT → WAITING_AT_ER → IN_TREATMENT → DISCHARGED
                                                   (or DECEASED via outcome model)
```

### Scene
`UNSECURED → SECURED` for violent incidents; secured at the hidden `scene_secured_tick` after police are on scene (police arrival + sampled 5–15 min). Non-violent scenes start secured.

### Responder teams
`IDLE → EN_ROUTE → ON_SCENE → RETURNING → IDLE`.

Every transition emits an event (Section 13).

---

## 8. Hospital model (`sim/hospital.py`)

- **Admission** requires every resource in `PatientNeeds` to be free at arrival. If not, the patient waits in the ER queue and the ambulance stays in `WAITING_AT_ER` until handover is possible or the patient can be placed.
- **Treatment durations** (sampled, then resources released): critical trauma: trauma bay 30–60 min, then OR 60–180 min if needed; serious: ER bed 60–180 min; minor: ER bed 30–90 min.
- **Staff loans:** a hospital may lend nurses to another hospital if, after the loan, it stays at or above `min_nurse_coverage`. Loans have a transfer delay (20–30 min) and a duration.
- **Walk-ins:** during an MCI, a share of minor patients (default 50–60%) self-transport to the hospital nearest the incident, arriving 15–45 min after the incident. They consume ER beds without an ambulance.
- **Baseline load:** each hospital starts with an initial occupancy (default 50–80%) and has background arrivals and discharges so capacity changes over time.

---

## 9. Travel, ETA, and calibration (`sim/travel.py`, `sim/calibrate.py`)

**Default travel model:** `minutes = haversine_km × 1.3 / speed_kmh × 60 × noise`, where emergency speed = 45 km/h, non-emergency return = 35 km/h, and `noise ~ lognormal(0, 0.15)` from the run's generator.

**Offload wait model (`WAITING_AT_ER`):** based on ER occupancy at arrival: below 80% → 5–12 min; 80–95% → 15–35 min; 95% or above → 35–60 min plus queue position. Configurable.

**Calibration (optional but planned):** `sim/calibrate.py` reads a downloaded sample of San Francisco Fire Department / EMS calls-for-service data (owner downloads it into `data/raw/`). It computes quantiles (median, p75, p90) for:
- dispatch → on scene (travel),
- on scene → transport (scene time),
- hospital arrival → unit available (turnaround proxy; includes cleanup, not only offload).

It writes `data/calibration.json`. If the file exists, `travel.py` samples from those quantiles; if not, it uses the defaults above. Clean data: drop missing/implausible intervals (keep 0.1–120 min), filter to medical units, deduplicate per call. Document everything in `ASSUMPTIONS.md`.

**`estimate_eta(unit_id, destination)`** returns `{median_min, p90_min}` from the same model. Exposed to agents and baselines alike.

**Optional street routes:** precompute once (OSMnx offline, or OSRM with light, one-time use) for all station/hospital/incident-site pairs into `data/routes.json` for map animation only. Never call a routing service during a run.

---

## 10. Scenario generator (`sim/generator.py`)

`generate(seed: int, demand: "normal" | "surge", info: "complete" | "partial") -> Scenario`, saved as `data/scenarios/seed_{seed:02d}_{demand}.json`.

### Hospitals (positions approximate real Boston hospital sites; names and all capacities are synthetic)

| ID | Approx. location | Owner | Capabilities | ER beds | Trauma bays | ORs | Trauma surgeons | Nurses | Notes |
|---|---|---|---|---|---|---|---|---|---|
| A | 42.3631, −71.0686 | Public | TRAUMA_L1, CARDIAC_CATH, STROKE, GENERAL | 10 | 3 | 3 | 3 | 8 | Main trauma center |
| B | 42.3496, −71.0632 | Public | GENERAL | 12 | 1 (stabilization only) | 0 | 0 | 6 | Community hospital |
| C | 42.3350, −71.0723 | Public | TRAUMA_L2, CARDIAC_CATH, GENERAL | 8 | 2 | 2 | 2 | 6 | Second trauma center |
| D | 42.3398, −71.1061 | Private | GENERAL | 10 | 0 | 2 (elective, protected) | 0 | 6 | Contract: up to 4 stable SERIOUS in a surge; no critical trauma |

Use generic names ("Hospital A", etc.). Coordinates are approximate; verify on a map before the demo.

### Fleet and teams
- City ambulances: AMB-1…AMB-5 (3 ALS, 2 BLS) at 3 stations spread across the map.
- Private firm "MedRide": PVT-1…PVT-3; `max_mutual_aid_units = 2`, `activation_minutes = 10`.
- Police: POL-1, POL-2. Fire: FIRE-1 (extrication).

### Demand
- **Normal:** 180-minute window, Poisson arrivals (default λ = 1 call per 12 min), mix of MEDICAL_CARDIAC, MEDICAL_STROKE, MEDICAL_GENERAL, FALL, VEHICLE_CRASH; 1–2 patients each.
- **Surge:** the normal stream, plus at tick 30 a SHOOTING (2 victims, violent) and at tick 35 a BUS_CRASH (~31 victims).
- **Severity:** simplified START-style assignment for MCIs (default bus crash mix ≈ 15–20% critical, 30–35% serious, 45–55% minor, 0–5% expectant); single-patient severity by incident type. True counts are hidden; `reported_victims` is noisy (±20%).
- **Initial fleet state:** some units start busy (drawn by the generator, then fixed in the scenario file) so starting conditions are explicit.

### Caller narratives (`agents/narratives.py`)
An LLM writes each incident's caller narrative from the hidden truth, in a realistic, imprecise voice (uncertain counts, panic, partial information). Generated once per scenario and stored in the scenario JSON. If no API key is available, use a template-based fallback.

---

## 11. Observation layer (`sim/observations.py`)

| Information | Complete setting | Partial-and-changing setting |
|---|---|---|
| Hospital capacity (for Dispatch/Allocator/baselines) | True, current | Status board published every 15 min (stale between updates) |
| Hospital's own state (for its own Hospital agent) | True, current | True, current |
| Victim counts and severity | True after call | Estimated from narrative until first unit on scene sends a scene report |
| Ambulance positions and states | True (vehicle location is realistic) | True |
| Scene secured | True, as an event | True, as an event |
| Walk-ins | Known on arrival | Known only to the receiving hospital until the next board update |

Baselines use the same observation object as the agents.

---

## 12. Validator hard rules (`sim/validator.py`)

Each check returns `(ok: bool, rule_id: str, reason: str)`. Every rejection is logged with its rule ID.

| Rule | Check |
|---|---|
| R1 | The unit exists, is in an assignable state, and isn't already committed elsewhere |
| R2 | The destination hospital has, or will have at expected arrival, every resource the patient needs (using true state at commit) |
| R3 | Critical trauma goes only to a hospital with a trauma bay *and* an available trauma surgeon; stabilization-only bays (Hospital B) only for the most unstable when no trauma center is reachable in time |
| R4 | Private contracts: firm units ≤ `max_mutual_aid_units`; private hospital limits and eligibility respected |
| R5 | No ambulance enters an unsecured violent scene; it stages instead |
| R6 | Mandatory human review, regardless of confidence, when (a) a critical patient would wait for a bay, or (b) a critical patient is routed past the nearest capable hospital by more than 10 min of ETA |
| R7 | Ambulance capacity: 1 critical or 2 non-critical patients |
| R8 | Staff loans keep the lender at or above `min_nurse_coverage` |
| R9 | No agent can create or modify capacity, staff, units, or scene status |

---

## 13. Event log (`sim/events.py`)

JSONL, one event per line: `{"run_id", "tick", "type", "actor", "payload"}`.

Event types (minimum): `CALL_RECEIVED`, `SCENE_REPORT`, `SCENE_SECURED`, `PRIORITY_REPORT`, `MESSAGE` (any protocol message), `PROPOSAL_VALIDATED`, `PROPOSAL_REJECTED` (with rule ID), `ESCALATED`, `APPROVED`, `OVERRIDDEN`, `FALLBACK_USED`, `COMMITTED`, `UNIT_STATE_CHANGED`, `PATIENT_STATE_CHANGED`, `HOSPITAL_STATUS`, `WALK_IN`, `STAFF_LOAN`, `MONITOR_ALERT`, `LLM_CALL` (agent, tokens, latency, cache hit), `RUN_SUMMARY`.

The log is enough to reconstruct the whole run for the dashboard (replay) and for metrics.

---

## 14. Agents and coordination

### 14.1 Messages (`protocol/messages.py`)

```python
class Message(BaseModel):
    message_id: str
    tick: int
    state_version: int          # engine state version the sender used
    sender: str                 # e.g. "dispatch", "hospital:B", "allocator"
    recipient: str              # agent id or "all"
    type: MessageType
    incident_id: str | None
    patient_ids: list[str] = []
    proposed_action: dict | None
    reason: str
    negotiation_round: int = 0
```

`MessageType`: `PRIORITY_REPORT`, `PROPOSE`, `ACCEPT`, `REJECT`, `COUNTER`, `ESCALATE`, `RESOLVE`, `STAFF_REQUEST`, `STAFF_RESPONSE`, `PRE_ALERT`, `STATUS`, `MUTUAL_AID_REQUEST`, `MUTUAL_AID_RESPONSE`.

A message whose `state_version` is older than the current engine state at commit triggers re-validation, not blind execution.

### 14.2 The agents

There are four LLM agent types and seven instances. Each is an SDK `Agent` with its own instructions file in `agents/prompts/`, its own read-only tools, and a Pydantic `output_type`.

| Agent | Triggered by | Read-only tools | Output type |
|---|---|---|---|
| **Assessment** (1) | `CALL_RECEIVED`, `SCENE_REPORT` | `get_incident`, `get_scene_reports` | `PriorityReport`: mode (SINGLE/MCI), estimated counts by severity, needs (police, fire), urgency 0–1, rationale |
| **Dispatch** (1) | new `PriorityReport`, unit becomes free, scene report | `get_available_units`, `estimate_eta`, `get_priority_queue`, `get_hospital_board` (observed) | `DispatchPlan`: list of `{unit_id, incident_id, patient_ids, target_hospital, eta_median, eta_p90, rationale}`, plus optional mutual-aid request |
| **Hospital** (4: A, B, C, D) | `PROPOSE` addressed to it, `STAFF_REQUEST`, own threshold crossed | `get_my_status`, `get_my_staff`, `get_my_incoming` (own data only) | `AdmissionDecision`: ACCEPT / REJECT / COUNTER with accepted patient IDs, counter-offer, rationale; or `StaffDecision` |
| **Allocator** (1) | conflicting proposals, unresolved after 3 rounds, MCI distribution plan | `get_pending_conflicts`, `get_offers`, `estimate_eta` | `Resolution`: assignments, unassigned patients, escalate flag, rationale |

**Instruction requirements:**
- Assessment has two paths: simplified single-patient urgency for normal calls, START-style estimates for MCIs. It never declares a scene safe.
- Hospital agents speak only for their own hospital. Public hospitals must accept emergencies within capacity and may hold reserve capacity for critical cases. Private hospital D follows its contract and protects elective capacity.
- Allocator objective (stated in its instructions and used by `confidence.py` for the margin term): minimize severity-weighted time to definitive care, subject to the hard rules, and avoid overloading any hospital.
- All agents explain decisions in one or two sentences in `rationale`.

**Not LLM agents:** ambulances, police, fire (rule-based, driven by the engine), the private firm's mutual-aid response (deterministic per contract), and the monitor.

### 14.3 Orchestrator (`agents/orchestrator.py`)

Plain Python, not an LLM. On each tick, after the engine advances, it collects trigger events and runs **decision cycles**:

1. New call → Assessment → `PriorityReport` broadcast.
2. Dispatch → `DispatchPlan`; mutual aid if needed.
3. For each proposal with a target hospital → that Hospital agent → ACCEPT / REJECT / COUNTER.
4. COUNTER or conflicts → revise (Dispatch) → up to 3 rounds (`protocol/negotiation.py`).
5. Still unresolved, or MCI distribution → Allocator → `Resolution`.
6. Confidence gate → approval (if needed) → validator → engine commit.
7. Engine emits `PRE_ALERT` from the ambulance to the receiving hospital.

Hospital agents for different hospitals may run concurrently (`asyncio.gather`). Each cycle has a step limit (`max_turns`) and a timeout.

### 14.4 Negotiation (`protocol/negotiation.py`)

```
PROPOSED → (ACCEPTED → done)
         → (REJECTED → revise or escalate)
         → (COUNTERED → revise, round += 1)
round > 3 → ESCALATE → Allocator RESOLVE
```

### 14.5 Confidence gate (`agents/confidence.py`)

Do **not** use the LLM's self-reported confidence. Compute:

```
score = 0.4 * consistency + 0.3 * margin + 0.2 * freshness + 0.1 * validator_clean
```
- `consistency`: for Allocator resolutions involving critical patients, sample k = 3 times and measure agreement; otherwise 1.0. (k is configurable to control cost.)
- `margin`: normalized objective gap between the chosen option and the second-best feasible option.
- `freshness`: 1.0 if hospital data is current, decaying linearly to 0 at 30 min old.
- `validator_clean`: 1.0 if no warnings, else 0.

Gate: ≥ 0.90 → execute; 0.75–0.90 → one information round (request a fresh hospital status or re-assessment), then recompute once; < 0.75 → human. Rule R6 forces human review regardless of the score. Weights and thresholds live in config.

### 14.6 Approval (`agents/approval.py`)

- `APPROVAL_MODE=interactive` (demo): the dashboard shows an approval card with the top two options and reasons; the human approves or picks the alternative. If no response in 60 simulated seconds, use the fallback.
- `APPROVAL_MODE=policy` (experiments): a documented fixed policy acts as the human. It picks the option with the better objective, computed from the *observed* state, after a 2-minute simulated delay. Log it as `APPROVED` with `approver="policy"`.

### 14.7 Fallbacks

On timeout, malformed output after one retry, or a validator rejection with no valid alternative: assign the nearest capable hospital with space, and the nearest free suitable unit. Log `FALLBACK_USED` with the reason. The fallback rate is a reported metric.

### 14.8 LLM caching and cost (`agents/llm_cache.py`)

- Cache key = hash(agent id, model, instructions version, serialized inputs).
- `LLM_MODE=record`: call the API and store responses. `cache_only`: never call the API; fail loudly on a cache miss. `live`: call the API and also store.
- Record tokens, latency, and cache hits per call (`LLM_CALL` events).
- Unit tests never call the real API; mock the runner.

---

## 15. Milestones (do these in order)

Each milestone ends with an acceptance check. Update `PROGRESS.md` when one passes.

### M0: Setup (Oct 19)
- Repo, virtual environment, `requirements.txt`, `.env.example`, `.gitignore` (`.env`, `logs/`, large raw data), `ruff` config, `CLAUDE.md`, `PROGRESS.md`.
- **Accept:** `pytest` runs; `ruff check .` passes.

### M1: Entities and state machines (Oct 19–20)
- `entities.py`, `state_machine.py`, `events.py`.
- Tests: illegal transitions raise; every transition emits an event.
- **Accept:** state machine tests pass.

### M2: Engine, hospital model, travel (Oct 20–21)
- Tick loop in this order: advance clock → complete transitions and move units → finish treatments and release resources → patient deterioration and outcome updates → new incidents, walk-ins, and scene events → collect decisions from the active policy → validate and commit → log.
- `hospital.py`, `travel.py` (defaults), `outcomes.py`.
- **Accept:** a hand-built mini-scenario (1 hospital, 1 ambulance, 1 call) completes the full ambulance lifecycle with correct timestamps.

### M3: Validator and generator (Oct 21–22)
- All rules R1–R9 with unit tests (one passing and one failing case each).
- `generator.py` for normal and surge; template narratives first (LLM narratives in M6).
- **Accept:** `python -m sim.generator --seed 7 --demand surge` writes a valid scenario; validator tests pass.

### M4: Observations, monitor, calibration (Oct 22–23)
- `observations.py` (both settings), `monitor.py` (alerts: hospital ≥ 90% full, ER wait > 20 min, zero free units in a district, surge detected), `calibrate.py` with fallback to defaults, `estimate_eta`.
- **Accept:** a test proves that in the partial setting the observed hospital board differs from true state between updates; `calibrate.py` runs on a small fixture CSV.

### M5: Baselines, metrics, CLI (Oct 23–24)
- `baselines/nearest.py`: nearest hospital with the required capability, ignoring load; nearest free unit.
- `baselines/rule_based.py`: strong, capacity-aware and capability-aware: severity-priority queue, nearest capable hospital with resources available at ETA, spreads non-critical patients across hospitals within +10 min of ETA, respects contracts, requests mutual aid when free units < pending critical patients.
- `eval/metrics.py` (Section 16).
- `run.py --policy {nearest,rule_based,agents_no_negotiation,agents} --demand {normal,surge} --info {complete,partial} --seed N` writes `logs/run_<id>.jsonl` and prints metrics.
- Reproducibility test: the same seed and policy produce an identical log (excluding wall-clock fields).
- **Accept (Phase 1 done):** `python run.py --policy rule_based --demand surge --info partial --seed 7` completes; all tests pass; baseline numbers differ between `nearest` and `rule_based` in the expected direction.

### M6: Agent models, tools, single agents (Oct 25–26)
- `agents/models.py`, `agents/tools.py` (all read-only, returning observation data only), prompts, `assessment.py`, `dispatch.py`, `hospital_agent.py`, `allocator.py`, `llm_cache.py`, LLM narratives.
- Each agent has a small script or test that runs it on a fixed input (mocked in tests, real in a manual check).
- **Accept:** each agent returns a valid typed output on a sample input; the cache replays identically in `cache_only` mode.

### M7: Orchestrator, negotiation, confidence, approval, fallbacks (Oct 27–28)
- `orchestrator.py`, `negotiation.py`, `confidence.py`, `approval.py`, fallback paths.
- `agents_no_negotiation` policy: same agents, but hospital COUNTER/REJECT ends the cycle (fall back to the rule-based choice) and no Allocator rounds.
- **Accept:** a surge run with `--policy agents` completes end to end.

### M8: Integration check (Oct 29)
- **Accept (Phase 2 done):** one surge run's log contains all of: an ambulance conflict between two incidents, a hospital COUNTER on capacity, a STAFF_REQUEST/RESPONSE, a mutual-aid exchange, a staged ambulance released by `SCENE_SECURED`, at least one ESCALATED decision, and zero commits that violate a rule. Write this check as an automated test over the log.

### M9: Experiments (Oct 30–Nov 1)
- `eval/run_experiments.py`: grid in Section 17; parallel where safe; resumable; records cost.
- `eval/report_tables.py`: results table (mean ± spread per metric per cell), calibration table, cost table → `results/`.
- **Accept:** `python eval/run_experiments.py --seeds 5` produces `results/summary.csv` and `results/summary.md`.

### M10: Dashboard (Oct 31–Nov 2)
See Section 18.
- **Accept:** `streamlit run app/streamlit_app.py` replays a surge run with all panels; interactive approval works in live mode.

### M11: Documentation and submission (Nov 3–4)
- README (problem, architecture diagram, setup, one-command runs, screenshots), `ASSUMPTIONS.md`, `ATTRIBUTION.md`, `docs/FUTURE_WORK.md`, short report (problem, related work, design, results, limitations).
- **Accept:** a clean clone, following only the README, can run a replay and the experiment summary.

---

## 16. Metrics (`eval/metrics.py`)

All computed from the event log.

| Metric | Definition |
|---|---|
| Response time | Call tick → first unit `ON_SCENE` (mean, median, p90; by severity) |
| Time to definitive care | Call tick → patient enters the required resource (trauma bay/OR for critical trauma, ER bed otherwise); by severity |
| Critical on-time rate | Share of critical patients reaching definitive care within 60 min (a modeled threshold) |
| Hospital overload minutes | Sum over hospitals of minutes with ER occupancy ≥ 100% or a non-empty queue |
| Ambulance minutes at ER | Total minutes in `WAITING_AT_ER` beyond the 10-minute base handover |
| Unserved calls | Calls with no unit on scene within 30 min, or patients not in care at run end |
| Modeled outcome score | Sum of synthetic survival probabilities from `sim/outcomes.py` (logistic decay with time to definitive care, parameters per severity). Clearly labeled as synthetic, not clinical |
| Conflicts and negotiation | Conflicts detected, resolved, rounds per resolution |
| Safety and reliability | Validator rejections by rule, fallback rate, escalations, overrides |
| Confidence calibration | For decisions in each confidence bin, the share that match the hindsight-best option (computed by a deterministic evaluator using true state at decision time) |
| Cost | LLM calls, tokens, latency, cache hit rate per run |

---

## 17. Experiment design (`eval/run_experiments.py`)

| Factor | Levels |
|---|---|
| Policy | `nearest` (reference) · `rule_based` (strong baseline) · `agents_no_negotiation` · `agents` |
| Information | `complete` · `partial` |
| Demand | `normal` · `surge` |
| Seeds | 5 (configurable) |

- Paired design: every policy runs on the same scenario files.
- Baseline runs are free; the LLM runs (2 policies × 2 × 2 × 5 = 40) use `LLM_MODE=record` and a small model. Run overnight.
- Report per cell: mean and spread for each metric. Answer H1–H3 directly in `results/summary.md`, including where the agents do *not* help.

---

## 18. Dashboard (`app/`)

**Modes:**
- **Replay** (default for presentation): load a `logs/run_*.jsonl`, with play/pause, speed (1×–8×), and a tick slider. No API calls.
- **Live:** run a scenario tick by tick with real agents; show agent statuses updating; interactive approval cards.

**Layout:**

| Area | Contents |
|---|---|
| Top bar | Scenario, policy, information setting, sim time, mode; KPI cards with the matching baseline value beside each |
| Left | **Live map:** pydeck on a free CARTO basemap (no API key). Hospitals (capacity ring), incidents by severity, ambulances via TripsLayer with fading trails, colored by state (empty / critical / serious / waiting at ER), routes to destinations. Interpolate smoothly between tick positions. Fallback: Plotly `scatter_map` with the `open-street-map` style, or a schematic grid. |
| Right | Agent activity cards (one per agent instance: status idle / thinking / waiting / decided, last message); human approval card; ambulance assignment cards (patient, severity, destination, ETA, reason) |
| Bottom tabs | Resources (beds, bays, ORs, surgeons, nurses per hospital; unit states) · Message feed (sender → recipient, type, reason) · Negotiation history (every proposal, counter, rejection, resolution) · Monitor alerts · Results (experiment tables and charts) |

**Proof that agents are real:** show the SDK tracing link for a live run, if tracing is enabled.

---

## 19. Testing strategy (`tests/`)

- **Invariants** (run after every tick in a test harness): no unit double-booked; no resource count below 0 or above capacity; no patient in two places; no unit inside an unsecured violent scene; every committed action passed the validator.
- **Validator:** one passing and one failing case per rule.
- **Reproducibility:** same seed + policy → identical log.
- **Observations:** partial view differs from truth between board updates; agents' tools never return hidden fields.
- **Agents:** mocked runner returns fixed outputs; check parsing, fallbacks on malformed output, timeouts.
- **Integration:** the M8 log check.
- Target: the whole suite runs in under 60 seconds without network access.

---

## 20. Working agreements for Claude Code

1. Follow this plan. If something is ambiguous or seems wrong, write the question at the top of `PROGRESS.md` and choose the simplest option that keeps the design principles; do not expand scope.
2. Build in milestone order. Do not start agents (M6) until M5 passes.
3. Write tests alongside code, starting with the engine invariants.
4. Never call the real OpenAI API in tests. Never print or commit secrets.
5. Keep every random draw on the run's seeded generator. No `random` module, no unseeded NumPy.
6. Keep agent tools read-only. Only `engine.commit()` changes state, and only after the validator passes.
7. Keep prompts in `agents/prompts/` as versioned files; include the prompt version in the cache key.
8. Prefer small, readable modules over clever abstractions. Type-hint everything.
9. After each milestone: run `ruff check .` and `pytest`, update `PROGRESS.md`, and summarize what changed.
10. Record every borrowed idea or snippet in `ATTRIBUTION.md` (source, license, what was used).

---

## 21. Documentation deliverables

- **ASSUMPTIONS.md:** synthetic hospitals and capacities (approximate real locations), fleet sizes, START-style simplified triage, outcome model is synthetic, calibration source and cleaning, turnaround as an offload proxy, walk-in share, approval policy, confidence weights.
- **ATTRIBUTION.md:** OpenAI Agents SDK (MIT) and any adapted example patterns; smooth-interpolation idea from God's Eye View (MIT); OpenStreetMap data (© OpenStreetMap contributors) and any routing tool used; San Francisco open data; Contract Net Protocol (Smith, 1980) as the basis of negotiation.
- **Report sections:** problem (offload delays, MCI patient distribution); related work (shared hospital status boards such as EMResource; research prototypes); design; experiment; results (H1–H3); limitations (simulation only, synthetic data, not clinically validated); future work.

---

## 22. Definition of done

- [ ] `python run.py --policy agents --demand surge --info partial --seed 7` completes end to end.
- [ ] `streamlit run app/streamlit_app.py` replays it with all panels and the live map.
- [ ] `python eval/run_experiments.py --seeds 5` produces the results tables.
- [ ] `pytest` passes; `ruff check .` passes.
- [ ] README, ASSUMPTIONS, ATTRIBUTION, and report are written.
- [ ] Submission text: repo link plus a short summary of results, including where agents did not help.
