# PROGRESS

## Open questions / decisions taken

1. **Package name clash.** PLAN §5 names the agent package `agents/`, but `openai-agents` installs
   as the importable module `agents`, so a local `agents/` would shadow the SDK.
   *Decision:* local package is `emerge_agents/`. All PLAN references to `agents/...` map to
   `emerge_agents/...`.
2. **Repo folder.** Built in place in `EMERGE-AI/` rather than a nested `emerge-ai/`.

## Milestones

- [x] M0 Setup
- [x] M1 Entities and state machines
- [ ] M2 Engine, hospital model, travel (checkpoint for review after this)
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
