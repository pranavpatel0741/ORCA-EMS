# CLAUDE.md — ORCA-EMS

Follow `PLAN.md` (single source of truth). Update `PROGRESS.md` when a milestone passes.

- Local agent package is `orca_agents/` (not `agents/`) because the OpenAI Agents SDK imports as `agents`.
- Run checks with `.venv/bin/ruff check .` and `.venv/bin/pytest`.
- Live dashboard: `.venv/bin/python dashboard_v2/run.py` (or the `dashboard` launch config). `app/` keeps only the shared state and map code it builds on.
- Scenario: `.venv/bin/python -m sim.generator --seed 7 --demand surge [--population 50000]`.
