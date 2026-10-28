# Future work

Ideas recorded instead of built (PLAN.md §2 froze the scope).

## Toward real use (staged)

1. **Simulation** (this project): find where agent negotiation helps and where it doesn't.
2. **Training and drills**: use the simulator for surge drills and dispatcher training.
3. **Shadow mode**: agents read real CAD and hospital status feeds but make no decisions. Their
   suggestions are compared with what humans did.
4. **Decision support**: agents suggest and humans decide, with approval cards like the
   dashboard's.
5. **Limited automation** for routine, low-risk choices. Critical cases stay with humans (R6).

Real use would need live data agreements, clinical validation, privacy protection, and clear
human accountability.

## Model and simulation

- Ambulance live tracking with realistic GPS / status-ping gaps (designed, then deferred by the owner).
- Inter-hospital transfers (e.g. stabilize at Hospital B, then move to a trauma center).
- Street-network travel times instead of straight-line distance × road factor.
- Calibrating travel times, not only scene and turnaround times, against real dispatch data.
- Regional mutual aid from neighboring towns, and air transport for critical trauma.
- Specialty units (burn, pediatric) and ICU beds as separate resources.
- LLM-written caller narratives (templates are used now; listed in PLAN as the first cut).
- Consistency sampling (k > 1) in the confidence gate, which costs more LLM calls.
- Demand forecasting, real-time external feeds, and learned policies were explicitly out of scope.
