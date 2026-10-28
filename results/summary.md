# ORCA-EMS results

40 runs · seeds [1, 2, 3, 4, 5] · policies ['nearest', 'rule_based']

> LLM agent runs are pending (set OPENAI_API_KEY and OPENAI_MODEL in .env and rerun). Only baselines are shown.

Synthetic simulation; the outcome score is a modeled survival sum, not a clinical measure. Mean ± standard deviation over seeds.

### Normal demand · complete information

| policy | deaths | outcome_score | critical_on_time | critical_care_mean | response_mean | overload_min | er_wait_over_base | not_in_care_end | capacity_failures | escalations | llm_calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nearest | 0.00 ± 0.0 | 2.91 ± 2.4 | 1.00 ± 0.0 | 58 ± 2.1 | 8.47 ± 3.7 | 322 ± 93.7 | 10 ± 14.5 | 0.00 ± 0.0 | 1.00 ± 1.4 | 0.00 ± 0.0 | 0.00 ± 0.0 |
| rule_based | 0.00 ± 0.0 | 2.90 ± 2.4 | 0.50 ± 0.7 | 61 ± 7.1 | 7.72 ± 2.7 | 327 ± 86.7 | 6.20 ± 13.3 | 0.00 ± 0.0 | 0.40 ± 0.5 | 0.40 ± 0.9 | 0.00 ± 0.0 |

### Normal demand · partial information

| policy | deaths | outcome_score | critical_on_time | critical_care_mean | response_mean | overload_min | er_wait_over_base | not_in_care_end | capacity_failures | escalations | llm_calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nearest | 0.00 ± 0.0 | 2.81 ± 2.3 | 0.00 ± 0.0 | 84 ± 23.3 | 9.62 ± 2.1 | 316 ± 97.3 | 37 ± 53.3 | 0.00 ± 0.0 | 0.80 ± 1.1 | 0.00 ± 0.0 | 0.00 ± 0.0 |
| rule_based | 0.00 ± 0.0 | 2.88 ± 2.3 | 0.00 ± 0.0 | 68 ± 0.7 | 9.62 ± 2.1 | 311 ± 90.8 | 9.80 ± 21.4 | 0.00 ± 0.0 | 0.20 ± 0.4 | 0.00 ± 0.0 | 0.00 ± 0.0 |

### Surge demand · complete information

| policy | deaths | outcome_score | critical_on_time | critical_care_mean | response_mean | overload_min | er_wait_over_base | not_in_care_end | capacity_failures | escalations | llm_calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nearest | 3.60 ± 3.9 | 29 ± 2.2 | 0.33 ± 0.0 | 62 ± 18.2 | 32 ± 24.9 | 644 ± 98.5 | 299 ± 61.5 | 8.00 ± 2.5 | 19 ± 2.5 | 2.80 ± 1.3 | 0.00 ± 0.0 |
| rule_based | 3.00 ± 2.5 | 31 ± 2.1 | 0.33 ± 0.0 | 67 ± 15.0 | 46 ± 20.0 | 709 ± 93.9 | 548 ± 164.6 | 5.60 ± 2.5 | 10 ± 3.2 | 4.40 ± 2.6 | 0.00 ± 0.0 |

### Surge demand · partial information

| policy | deaths | outcome_score | critical_on_time | critical_care_mean | response_mean | overload_min | er_wait_over_base | not_in_care_end | capacity_failures | escalations | llm_calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nearest | 3.80 ± 3.1 | 29 ± 2.4 | 0.37 ± 0.2 | 63 ± 16.6 | 25 ± 22.6 | 620 ± 117.9 | 288 ± 80.9 | 8.40 ± 2.5 | 20 ± 5.3 | 3.20 ± 1.5 | 0.00 ± 0.0 |
| rule_based | 3.60 ± 3.1 | 30 ± 2.2 | 0.37 ± 0.2 | 63 ± 16.1 | 48 ± 21.7 | 707 ± 116.4 | 536 ± 131.4 | 6.20 ± 2.6 | 9.80 ± 2.7 | 4.40 ± 2.4 | 0.00 ± 0.0 |

## Hypotheses

Paired comparisons on identical scenarios (same seed). With few seeds this is descriptive evidence, not a significance test.

**H1. Negotiation reduces unresolved conflicts and capacity-related failures** (agents vs agents without negotiation, all cells).
- Verdict: not tested yet (runs missing)
- capacity_failures: no paired runs yet
- overload_min: no paired runs yet

**H2. Negotiation improves time to definitive care for critical patients during scarcity** (surge cells).
- vs rule_based: verdict not tested yet (runs missing); critical_care_mean: no paired runs yet; critical_on_time: no paired runs yet
- vs agents_no_negotiation: verdict not tested yet (runs missing); critical_care_mean: no paired runs yet; critical_on_time: no paired runs yet

**H3. The benefit is larger under surge and partial information** (agents vs rule_based, outcome score).
- normal / complete: outcome_score: no paired runs yet
- normal / partial: outcome_score: no paired runs yet
- surge / complete: outcome_score: no paired runs yet
- surge / partial: outcome_score: no paired runs yet
- Verdict: not tested yet (runs missing)

## Confidence calibration (agents)

No agent decisions with confidence scores yet.

## Cost per run

| policy | LLM calls | tokens | wall seconds |
|---|---|---|---|
| nearest | 0 | 0 | 0.1 |
| rule_based | 0 | 0 | 0.1 |
