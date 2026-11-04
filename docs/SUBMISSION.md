# ORCA-EMS submission

**Repository:** https://github.com/pranavpatel0741/ORCA-EMS

ORCA-EMS (Orchestrated Response and Capacity Allocation) is a simulator in which AI agents
built on the OpenAI Agents SDK coordinate ambulances and hospitals in a fictional town of
50,000. An Assessment agent triages calls, a Dispatch agent assigns ambulances and proposes
hospitals, Hospital agents accept, reject or counter based on their own beds and staff, and an
Allocator settles disagreements. Safety rules check every decision, risky ones go to human
review, and a rule-based backup takes over when an agent's answer is unusable. Every message
is labeled with who produced it, and every model answer is saved for replay.

**Results** (5 seeds × 2 demand levels × 2 information settings, gpt-4o-mini, current code,
about $1 in total):
- With incomplete hospital information on a normal day, the agents got every critical patient
  into care within 60 minutes; neither baseline did, and critical care came 15–31 minutes sooner.
- In a mass-casualty surge, negotiation reduced ambulance time waiting at ER doors (504 vs 558
  minutes with incomplete information) and brought critical patients to care 3–5 minutes sooner
  on average than the same agents without negotiation.
- **Where agents did not help:** in a surge with incomplete information they sent the first
  ambulance later than the baselines (62–70 vs 25–48 minutes) and deaths were about the same.
  With complete information they added little over the rule-based policy. Hypotheses H1 and H3
  were not supported; H2 was mixed.
- A self-audit before the final run found and fixed problems in how agent answers were checked
  and in two metrics (`docs/AGENT_EVAL_AUDIT.md`); all results above use the fixed code.

Five seeds and one model make this descriptive evidence. The simulation, patients and outcome
model are synthetic and not clinically validated. See `docs/REPORT.md` and `results/summary.md`.

**Run it:** follow `README.md`. Without an API key, saved runs replay on the dashboard, the
guided demo runs offline, and `LLM_MODE=cache_only` reuses the saved model answers.
