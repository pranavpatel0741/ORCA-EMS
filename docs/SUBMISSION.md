# ORCA-EMS submission

**Repository:** https://github.com/pranavpatel0741/ORCA-EMS

ORCA-EMS (Orchestrated Response and Capacity Allocation) is a simulator in which AI agents
built on the OpenAI Agents SDK coordinate ambulances and hospitals in a fictional town of
50,000. An Assessment agent triages calls, a Dispatch agent assigns ambulances and proposes
hospitals, Hospital agents accept, reject or counter based on their own beds and staff, and an
Allocator settles disagreements. Safety rules check every decision, risky ones go to human
review, and a rule-based backup takes over when an agent's answer is unusable. Every message
is labeled with who produced it, and every model answer is saved so runs replay exactly.

**Results** (5 seeds × 2 demand levels × 2 information settings, gpt-4o-mini, about $0.80 in
total). These come from the grid recorded before a self-audit fixed answer grounding and two
metrics (`docs/AGENT_EVAL_AUDIT.md`); they are labeled historical until the grid is re-run:
- With incomplete hospital information on a normal day, the agents got every critical patient
  into care within 60 minutes; neither baseline did, and critical care came 12–28 minutes sooner.
- In a mass-casualty surge with incomplete information, negotiation brought critical patients
  to care 11 minutes sooner than the same agents without negotiation, with less ambulance time
  waiting at ER doors.
- **Where agents did not help:** in a surge, they sent the first ambulance later than the
  baselines (54–60 vs 25–48 minutes) and deaths were about the same. With complete information
  they added nothing over the rule-based policy. Hypothesis H3 (a larger benefit under surge)
  was not supported.

Five seeds and one model make this descriptive evidence. The simulation, patients and outcome
model are synthetic and not clinically validated. See `docs/REPORT.md` and `results/summary.md`.

**Run it:** follow `README.md`. Without an API key, `LLM_MODE=cache_only` replays the recorded
agent runs on the dashboard and reproduces the results tables.
