# PROGRESS — ORCA-EMS

ORCA-EMS: Orchestrated Response and Capacity Allocation (formerly EMERGE-AI).

## Owner decisions (2026-10-20, after the M2 review)

- **Offload:** realism first. The crew stays with its patients until the hospital takes every
  one into care. The crowding band (PLAN §9) is the minimum wait. There is **no cap**: an
  ambulance can be out of service as long as real ramping lasts, and the patient keeps
  deteriorating meanwhile.
- **R6 for baselines:** same approval path and delay as agents (fairness). Built in M7.
- **Hospital D:** takes ambulance patients only under its surge contract, during an active
  surge (bus crash or shooting active). Walk-ins can still arrive there.
- **Hospital B stabilization bay:** counts as definitive care for survival, but is reported
  separately and excluded from the critical on-time rate (`stabilization_only` flag on the
  IN_TREATMENT event).
- **min_nurse_coverage:** half the nurses, rounded up (reviewer default; owner did not object).

## Owner decisions (2026-10-22)

- **Town:** a fictional 20 × 20 km town, default 50,000 people (cheap LLM runs). The 4 hospital
  roles are kept; all resources are derived from U.S. per-capita figures in `sim/town.py`
  (see ASSUMPTIONS.md). Real scarcity is accepted: nothing is tuned to make the surge easy or
  impossible.
- **Ward beds and ER boarding** were added so the 114 staffed beds matter.
- **Out of scope:** ambulance live tracking / GPS telemetry; the dispatcher keeps exact unit
  status.
- **Dashboard early (M10 before M4–M9):** a live Streamlit dashboard centered on per-call
  agent communication, with live hospital capacity, a simple grid map, and per-call handling
  times. The nearest baseline (part of M5) drives it until agents exist.

## Decisions taken (judgment calls)

1. **Package name clash.** `openai-agents` imports as `agents`, so the local package is
   `orca_agents/`. All PLAN references to `agents/...` map to `orca_agents/...`.
2. **Repo folder.** Built in place in `EMERGE-AI/`; it can be renamed to `ORCA-EMS/` at any time.
3. **R2 all-full clause.** R2 passes if the hospital is projected to have resources at ETA
   (free now + releases before ETA − queue − committed incoming). If *no fully capable
   hospital* passes that test, any fully capable one passes with a structured warning
   `{R2, warn, ALL_FULL}` and the patient queues. R6(a) flags it for review when critical.
   "Fully capable" = capability + resource types + not a stabilization-only bay for trauma +
   contract allows it.
4. **Offload:** see owner decision. Implemented as: WAITING_AT_ER lasts at least the crowding band,
   then holds until every onboard patient is IN_TREATMENT or DECEASED.
5. **Nurses:** slots; each nurse covers 2 patients; a critical patient takes 2.
6. **Critical trauma:** trauma bay + surgeon at admission; after the bay phase the patient moves
   to an OR (bay released, surgeon and nurses kept) or keeps the bay until an OR frees. Only
   50% of critical trauma patients need an OR within 60 min (generator).
7. **Deaths:** deterministic: untreated and survival < 0.05 → DECEASED. Survival is frozen at
   definitive care; treated patients never die. No random death draws.
8. **Crew triage:** if a unit arrives with no live assigned patients, the crew picks the most
   severe unassigned waiting patients within R7. Any destination not validated for that exact
   patient set is cleared, so a validated RouteToHospital is required.
9. **Re-validation (PLAN §14.1):** at the end of loading, the engine re-runs the validator on
   the destination. A block clears it and the policy must route again.
10. **Actions:** `sim/actions.py` holds `Dispatch`, `RouteToHospital`, `LendStaff`,
    `ActivateMutualAid`. Actions are frozen and forbid extra fields.
11. **State machine additions:** LOADING→RETURNING and TRANSPORTING→RETURNING, used only when
    every patient died (or was taken by another unit).
12. **Randomness:** named streams (`travel`, `background`, `staff`, `misc`) and per-patient
    common random numbers (scene, loading, offload, handover, treatment). Background load and
    patient durations are policy-independent. Travel noise necessarily depends on which trips a
    policy makes. Generator: one stream per purpose, plus per-incident sub-streams for reported
    counts and narratives, so the surge file contains the normal file exactly.
13. **R3 when trauma centers are saturated:** R3 blocks only *structural* misrouting (a non-trauma
    center, or misuse of Hospital B's stabilization bay). Projected bay/surgeon shortfalls are
    R6(a) reviews and late ORs are `{R3, review, OR_LATE}`, not blocks. Blocking them could leave
    a loaded unit with no legal destination. B exception = most unstable (lowest survival among
    the incident's untransported critical patients) AND no trauma center can start definitive care
    within `or_within_minutes` (else 60) of the call.
14. **R5:** the engine stages units at unsecured violent scenes (`scene_entry_allowed`). The
    validator adds a `{R5, warn, STAGING}` flag on such dispatches.
15. **R6:** returns `level=review` (codes `R6a`, `R6b`) and is logged in PROPOSAL_VALIDATED.
    In M3 the commit still proceeds; M7 adds approval gating before commit.
16. **R9:** unknown action types are blocked; the engine fingerprints state before/after
    `policy.decide` and raises `R9Violation` on any change.
17. **Start-of-run busy units** are RETURNING only (generator and engine enforce this).

## Done in M4 (from review)

- `Policy.decide(obs)` with a frozen observation instead of the engine (principle 2); the test
  greedy policy currently reads true severity.
- Policies see rule id + code only; full rejection reasons (may contain hidden truth) stay in
  the log.

## Milestones

- [x] M0 Setup
- [x] M1 Entities and state machines
- [x] M2 Engine, hospital model, travel (+ review fix pass)
- [x] M3 Validator and generator
- [x] M4 Observations, monitor, calibration
- [x] M5 Baselines, metrics, CLI
- [x] M6 Agent models, tools, single agents (offline-tested; live LLM check needs a key)
- [x] M7 Orchestrator, negotiation, confidence, approval, fallbacks
- [x] M8 Integration check (automated, scripted backend)
- [~] M9 Experiments (grid + tables done; baselines run; LLM runs pending a key)
- [x] M10 Dashboard (live, replay, agents, interactive approval)
- [~] M11 Documentation (README, report draft, attribution, assumptions done; final results pending)

## Log

- **M0 (2026-10-19):** repo, Python 3.11 venv (uv), pinned requirements, ruff/pytest config,
  `.env.example`, `config/settings.py`, package skeleton.
- **M1 (2026-10-19):** entities, event log, explicit state machines. 138 tests.
- **M2 (2026-10-19):** travel, hospital, outcomes, actions, validator R1/R2/R7, engine,
  invariants harness, hand-checked lifecycle test. 146 tests.
- **M2 review (2026-10-20):** external review found 7 blockers (all confirmed by probes) and 13
  should-fix items; see `docs/review/M2_REVIEW_PROMPT.md` for the prompt. All blockers and
  should-fix items fixed except the two deferred to M4 above. The nits were fixed too (staging
  re-route on secure, single RUN_SUMMARY, arrival-sequence tie-break, steady-state initial
  stays). Died patients keep `ambulance_id`/`hospital_id` as history (documented).
- **M3 (2026-10-20):** validator R1–R9 with levels/codes; `ActivateMutualAid` + engine
  activation; `sim/generator.py` (hospitals A–D, fleet, normal Poisson demand, surge shooting +
  bus crash, START mix, noisy reports, walk-ins, busy units, template narratives, scenario
  validator, CLI). Acceptance: `python -m sim.generator --seed 7 --demand surge` writes a valid
  scenario; files are byte-identical across `PYTHONHASHSEED`; the surge file contains the normal
  stream exactly; R1–R9 pass/fail matrix; greedy surge run holds all invariants.
  173 tests in ~2 s.
- **Town + dashboard (2026-10-22):**
  - population-based town profile (`sim/town.py`)
  - generator derives hospitals and fleet from it (50k default, `--population`)
  - ward beds and ER boarding; ED nurse ratio 1:4
  - protocol `Message` schema; engine messages use it
  - nearest baseline (`baselines/nearest.py`)
  - per-call handling metrics (`eval/handling.py`) and wall-clock decision timing
  - dashboard: `app/state.py`, `app/map_view.py`, `app/panels.py`, `app/streamlit_app.py`
  
  Checked in the browser:
  - call threads fill in live
  - capacity cards update on admission
  - the feed shows calls, commits, validator rejections, pre-alerts and scene events
- **Dashboard redesign (2026-10-22):** CAD-style dispatch screen modeled on real systems
  (CAD incident queue + map + remarks feed; EMResource-style hospital board; EMTrack-style
  MCI triage and transport summary).
  - Runs start from an incident picker (`sim/presets.py`): cardiac arrest, two-car crash,
    shooting, school bus crash, bus crash + shooting, normal day.
  - Seed, population and policy are under a collapsed "Advanced" sidebar.
  - The conversation is rewritten as plain radio-style lines between roles (911 caller,
    Dispatch, ambulances, hospitals, safety rules, police).
  - Hospital replies (accept / counter) will come from the hospital agents in M6–M7; they are
    not faked.
- **M4 (2026-10-28):** `sim/observations.py`. Policies now decide from a frozen
  `Observation`:
  - complete info: live board, victims known at the call
  - partial info: board refreshed every 15 min, victims known after the scene report,
    walk-ins visible at the next update
  - rejections come back as rule codes only
  
  Also `sim/monitor.py` (alerts: hospital full, ER wait, no free unit in a district, surge)
  and `sim/calibrate.py` (DataSF quantiles; falls back to default timing).
- **M5 (2026-10-28):** `baselines/rule_based.py`, `eval/metrics.py` (PLAN §16, from the log
  only), `run.py`, and a cross-process reproducibility test. Seed 7 surge, partial info:
  rule-based had fewer deaths and capacity failures than nearest but slower response
  (reported, not tuned).
- **M6–M7 (2026-10-28):** `orca_agents/`:
  - models, versioned prompts, read-only tools
  - LLM cache (live / record / cache_only)
  - the four agents
  - orchestrator: assessment, dispatch, hospital PROPOSE / ACCEPT / COUNTER (up to 3
    rounds), allocator, staff requests, mutual aid, confidence gate, fallbacks
  - scripted offline stand-in for tests
  
  Engine approval queue: R6 or low-confidence decisions wait 2 min, then the policy approves
  or overrides; interactive mode is used on the dashboard. Also a hindsight-best evaluator for
  confidence calibration. Decisions:
  - the confidence gate applies to routes carrying critical patients
  - k = 1, so consistency is 1.0
  - a unit is negotiated once; after a rule rejection it is re-routed by the rule-based choice
    (this prevents loops and bounds LLM cost: ~80–170 calls per surge run with the stand-in)
- **M8 (2026-10-28):** `tests/test_integration.py`. A negotiated surge log contains:
  - an ambulance conflict between two calls
  - capacity COUNTERs
  - a STAFF_REQUEST / RESPONSE (test fixture with a short nurse roster)
  - a mutual-aid exchange
  - a staged unit released by SCENE_SECURED
  - escalations
  - no rule-violating commits
- **M9 (2026-10-28):** `eval/run_experiments.py` (resumable, paired, parallel baselines,
  sequential LLM runs) and `eval/report_tables.py` (summary.csv / summary.md, H1–H3 paired
  verdicts, calibration and cost). Baseline results for 5 seeds are committed. Scripted dry
  runs go to `results/scripted/` (gitignored).
- **M10–M11 (2026-10-28):** the dashboard gains agent policies (OpenAI when a key is set,
  otherwise a labeled offline stand-in) and interactive approval cards. Added README,
  ATTRIBUTION, FUTURE_WORK, a report draft, and extended ASSUMPTIONS.
- **Cut, per PLAN's cut list:** LLM-written caller narratives (templates are used) and
  consistency sampling k > 1.
- **Live agents (2026-10-29 – 10-31):** gpt-4o-mini. Fixes from reading transcripts: one
  shared event loop, dispatch without tools, hospitals each ambulance can be treated at,
  no re-proposing a hospital that declined, explicit list of ambulances to route, failed calls
  cached. Dashboard: source label on every message (AI / rule backup / stand-in / sim), AI
  activity tab with each call's input and answer, negotiation threads, talk graph, real-time
  and fast paces, saved runs with transcript and scorecard (`results/runs_saved/`).
- **M9 accepted (2026-10-31):** 5-seed grid with gpt-4o-mini, 80 runs, about $0.80.
  `results/summary.md`; REPORT §5 filled in, including where agents did not help. A clean
  clone replays the grid with `LLM_MODE=cache_only` and no key.
- **Demo:** Cardiac arrest, Shooting, School bus crash are cached for the dashboard's
  "AI agents, negotiating (OpenAI)" setting and replay free.
