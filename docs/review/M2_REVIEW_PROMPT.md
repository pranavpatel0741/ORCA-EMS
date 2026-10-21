# Review prompt: ORCA-EMS after M2, and the plan for M3

> **How to use:** paste everything below the line into a reviewer session.
> - **Claude Code opened in this folder:** paste as is. It can read the files itself.
> - **A chat without file access:** also attach `PLAN.md`, `PROGRESS.md`, `sim/engine.py`,
>   `sim/hospital.py`, `sim/validator.py`, `sim/travel.py`, `sim/outcomes.py`,
>   `sim/state_machine.py`, `tests/invariants.py`, and `tests/test_engine.py`.

---

You are reviewing **ORCA-EMS (Orchestrated Response and Capacity Allocation)**, a course
mid-term due **Nov 4, 2026, 18:00**. It simulates ambulance-to-hospital coordination with
multiple agents negotiating. `PLAN.md` is the source of truth. Milestones M0–M2 are built:
- entities and state machines
- a deterministic tick engine
- the hospital capacity model
- travel times
- the synthetic outcome model
- validator rules R1, R2 and R7

There are 146 passing tests. Judgment calls are listed in `PROGRESS.md` under "Open
questions / decisions taken".

There are two parts: **(A)** review M2, then **(B)** plan M3. Do not write implementation
code. Report findings and a plan only.

## Ground rules

- Judge everything against `PLAN.md` §3 (core design principles):
  - the engine is the only source of truth
  - agents see observations, not hidden truth
  - hard rules beat AI
  - runs are seeded and reproducible
  - simulated time is not wall-clock time
  - comparisons with baselines are fair
  - outcomes are honest
- Scope is frozen (PLAN §2). Do not suggest features outside it. Put ideas for later under
  "Future work".
- Do not recommend tuning parameters so that one policy beats another. The experiment must
  stay unbiased.
- Mark every finding with a severity:
  - **Blocker:** wrong results, broken invariants, or breaks a later milestone
  - **Should fix:** a real modeling or design issue
  - **Nit:** style or naming
- Cite `file:line` and give a concrete failure scenario for each finding: the inputs or state,
  and the wrong outcome.

## Part A: what to review

### A1. Correctness of the tick loop (`sim/engine.py`)
1. Is the tick order the same as PLAN §15 M2? Could any step read state that a later step in
   the same tick should already have changed? Example: an ambulance arrives in step 2 and its
   patient is admitted in step 3 of the same tick. Is that intended and consistent?
2. Can any unit get stuck? Check a unit held in `ON_SCENE` waiting for extrication, a unit held
   in `LOADING` waiting for a destination, and a unit in `STAGING` at a scene that never gets
   secured.
3. Reassignment: when a unit already `EN_ROUTE` or `STAGING` is sent to a new incident, are the
   old patients' assignments released correctly? Can two units claim the same patient?
4. Deaths: are patients removed cleanly from ambulances, hospital queues, and incident
   bookkeeping?
5. Incident closing and police/fire returning home: can an incident close while patients are
   still waiting, or never close at all?

### A2. The modeling decisions in `PROGRESS.md` (items 3–10)
For each decision, say whether to **keep, change, or drop** it, and give the reason.
Pay particular attention to:
- **R2 "all-full clause":** when no hospital has projected capacity, any hospital with the
  right resource types passes. Is this defensible, or does it hide failures the metrics should
  show?
- **Offload model:** the crew waits the time set by ER crowding, then leaves; an unadmitted
  patient stays in the ER queue. PLAN §8 says the ambulance stays "until handover is possible."
  Does this under-count offload delay?
- **Trauma surgeon held through the trauma bay *and* the OR phase.** In a stress test this made
  surgeons the bottleneck, and one critical patient died waiting. Is that realistic, or too
  harsh?
- **Deterministic death threshold** (survival < 0.05) instead of random death draws.
- **Nurse slots** (one nurse covers two patients; a critical patient takes two).
- **First unit on scene sets `unit_on_scene` for all waiting victims.** This changes what the
  response-time metric means in a mass-casualty incident (MCI).
- **On-scene crew triage happens inside the engine, not as a validated commit.** Does that
  conflict with "every committed action passed the validator"?

### A3. Fairness and reproducibility
- `eta_tick_for` (used by R2) assumes the shortest scene and loading times. Is it biased?
  Will baselines and agents get the *same* ETA function, as PLAN §9 requires?
- Is every random draw on the run's seeded generator? Could the order of draws change
  depending on the policy in a way that breaks the paired experiment design (same scenario,
  different policy)? Example: travel noise is drawn at dispatch time, so different decisions
  shift every later draw. Is that acceptable, or should random streams be split per entity or
  purpose?
- Are there wall-clock fields or non-deterministic iteration orders (dict or set ordering) in
  the log?

### A4. Hospital model (`sim/hospital.py`)
- Is the `projected_free` logic correct? It counts releases before the ETA, minus the current
  queue, minus already-committed incoming patients. Does it double-count, or ignore
  background arrivals?
- The ER queue is ordered by severity with no head-of-line blocking. Can a background patient
  take a bed ahead of a scenario patient?
- Staff loans: returns are deferred while the borrower's nurse slots are full. Can a loan
  never return? Is the lender's coverage still correct during the loan?

### A5. Tests (`tests/`)
- Do the invariants in `tests/invariants.py` really cover PLAN §19? What is missing?
- Is the hand-checked lifecycle test truly computable by hand?
- Name the three most valuable tests that are still missing for M2.

### A6. Readiness for later milestones
- Will this engine support M4 partial observations (a status board refreshed every 15 min)?
  Will it support M5 metrics computed *only from the event log*? Name any event or payload
  field the logs are missing. Examples: are offload minutes recoverable? Are hospital
  occupancy snapshots enough to compute "overload minutes"?
- Is the `Action` set (`Dispatch`, `RouteToHospital`, `LendStaff`) enough for M7 negotiation
  and mutual aid, or is an action type missing?

## Part B: plan M3 (validator and generator)

Using PLAN §10, §12 and §15 M3, plus your findings from Part A, write the M3 plan:

1. **Fixes first:** which Part A blockers and should-fix items must land before M3 code, in
   what order.
2. **Validator R3–R9:** for each rule, give the exact check, the engine data it reads, edge
   cases, and one passing and one failing test case. Cover in particular:
   - R3: Hospital B's stabilization-only bay exception ("most unstable" plus "no trauma center
     reachable in time"; define both precisely)
   - R4: private firm and contract limits, including how mutual aid activates private units
     (`activation_minutes`)
   - R5: staging (already in the engine; what does the validator add?)
   - R6: human-review triggers. The validator flags; approval is M7. How is the flag
     represented now?
   - R9: how to enforce "agents cannot modify capacity"
3. **Generator (`sim/generator.py`):**
   - hospitals A–D and the fleet exactly as PLAN §10
   - normal demand: Poisson, λ = 1 call per 12 min, 180 min
   - surge demand: a shooting at tick 30 and a ~31-victim bus crash at tick 35, with
     START-style severity mix
   - noisy `reported_victims`
   - needs per incident type
   - walk-ins (50–60% of MCI minor patients)
   - some units busy at the start
   - template narratives
   - file naming `data/scenarios/seed_{seed:02d}_{demand}.json` and the CLI
   
   State what is drawn from which random stream so the scenario files are reproducible.
4. **Acceptance:** list the checks that prove M3 is done, including
   `python -m sim.generator --seed 7 --demand surge` and the R1–R9 test matrix.
5. **Risks to the deadline:** the top three risks for M3–M5, and what to cut first if time
   runs short. Do not cut anything PLAN.md lists as required by the assignment.
6. **A short outline of M4 and M5** with any design changes your review suggests.

## Output format

1. **Summary verdict:** 3–5 sentences. Is M2 a sound foundation? Can M3 start?
2. **Findings table:** severity | area | `file:line` | issue | failure scenario | suggested fix.
3. **Decision verdicts:** keep, change, or drop for each item in PROGRESS.md, with a one-line
   reason.
4. **M3 plan:** numbered steps, each with an acceptance check.
5. **Questions for the owner:** only decisions that are genuinely the owner's to make.
