# PROGRESS — ORCA-EMS

ORCA-EMS: Orchestrated Response and Capacity Allocation (formerly EMERGE-AI).

## Open questions / decisions taken

1. **Package name clash.** PLAN §5 names the agent package `agents/`, but `openai-agents` installs
   as the importable module `agents`, so a local `agents/` would shadow the SDK.
   *Decision:* local package is `orca_agents/`. All PLAN references to `agents/...` map to
   `orca_agents/...`.
2. **Repo folder.** Built in place in `EMERGE-AI/` rather than a nested `orca-ems/`; the folder can be renamed
   to `ORCA-EMS/` at any time (nothing depends on its name).
3. **R2 when every hospital is full (M2).** Strict "resources free at ETA" would leave loaded
   ambulances with no legal destination during a surge. *Decision:* R2 passes if the hospital is
   projected to have the resources at ETA (free now + releases before ETA − queue − committed
   incoming), OR if no structurally capable hospital passes that test, in which case any
   structurally capable hospital passes and the patient queues (logged as "all-full clause").
   R6(a) will force human review when this happens to a critical patient.
4. **Offload model (M2).** The ambulance waits the occupancy-band time from PLAN §9, then hands
   over; an unadmitted patient stays in the ER queue under hospital care. The crew is not held
   until a bed frees.
5. **Nurses (M2).** Modeled as slots: each nurse covers 2 patients; a critical patient takes 2.
6. **Critical trauma (M2).** Trauma bay + surgeon at admission; after the bay phase the patient
   moves to an OR (bay released, surgeon kept) or keeps the bay until an OR frees.
7. **Deaths (M2).** Deterministic: an untreated patient is DECEASED when synthetic survival
   probability < 0.05. Survival is frozen at definitive care. No random death draws.
8. **Crew triage (M2).** If a unit arrives with no assigned patients (or they were taken), the
   on-scene crew picks the most severe unassigned waiting patients within R7 capacity.
9. **Actions module (M2).** `sim/actions.py` (not in PLAN §5) holds `Dispatch`,
   `RouteToHospital`, `LendStaff`, shared by validator, engine, policies, and agents.
10. **State machine addition (M2).** LOADING→RETURNING, used only if all loaded-to-be patients
    died or were taken by another unit.

## Milestones

- [x] M0 Setup
- [x] M1 Entities and state machines
- [x] M2 Engine, hospital model, travel (checkpoint for review after this)
- [ ] M3 Validator and generator
- [ ] M4 Observations, monitor, calibration
- [ ] M5 Baselines, metrics, CLI
- [ ] M6 Agent models, tools, single agents
- [ ] M7 Orchestrator, negotiation, confidence, approval, fallbacks
- [ ] M8 Integration check
- [ ] M9 Experiments
- [ ] M10 Dashboard
- [ ] M11 Documentation and submission

## Log

- **M0 (2026-10-19):** repo, Python 3.11 venv (uv), pinned requirements, ruff/pytest config,
  `.env.example`, `config/settings.py`, package skeleton.
- **M1 (2026-10-19):** `sim/entities.py` (Pydantic models + enums), `sim/events.py` (EventLog,
  JSONL), `sim/state_machine.py` (explicit transition tables; one event per transition; patient
  timestamps set on entry). Design choices: EN_ROUTE→EN_ROUTE is an empty reassignment;
  STAGING releases into a short EN_ROUTE leg; walk-ins go WAITING_ON_SCENE→WAITING_AT_ER.
  138 tests pass.
- **M2 (2026-10-19):** `sim/travel.py`, `sim/hospital.py`, `sim/outcomes.py`, `sim/actions.py`,
  `sim/validator.py` (R1, R2, R7), `sim/engine.py` (tick loop, commit API, police/fire,
  staging, extrication, walk-ins, staff loans, background load). `tests/invariants.py` runs
  after every tick. Lifecycle test with deterministic timing matches hand-computed timestamps.
  146 tests pass.
