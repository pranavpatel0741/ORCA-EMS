# ORCA-EMS results

80 runs · seeds [1, 2, 3, 4, 5] · policies ['nearest', 'rule_based', 'agents_no_negotiation', 'agents']

Synthetic simulation; the outcome score is a modeled survival sum, not a clinical measure. Mean ± standard deviation over seeds.

`capacity_failures` is a composite proxy: R2 rejection events plus patients still awaiting care. It is not a count of distinct affected patients. Treatment time averages include only patients reaching definitive care; read them alongside deaths and patients not in care.

### Normal demand · complete information

| policy | deaths | outcome_score | critical_on_time | critical_care_mean | response_mean | overload_min | er_wait_over_base | not_in_care_end | capacity_failures | escalations | llm_calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nearest | 0.00 ± 0.0 | 2.91 ± 2.4 | 1.00 ± 0.0 | 58 ± 2.1 | 8.47 ± 3.7 | 322 ± 93.7 | 10 ± 14.5 | 0.00 ± 0.0 | 1.00 ± 1.4 | 0.00 ± 0.0 | 0.00 ± 0.0 |
| rule_based | 0.00 ± 0.0 | 2.90 ± 2.4 | 0.50 ± 0.7 | 61 ± 7.1 | 7.72 ± 2.7 | 327 ± 86.7 | 6.20 ± 13.3 | 0.00 ± 0.0 | 0.40 ± 0.5 | 0.40 ± 0.9 | 0.00 ± 0.0 |
| agents_no_negotiation | 0.00 ± 0.0 | 2.91 ± 2.4 | 0.50 ± 0.7 | 57 ± 8.5 | 11 ± 3.5 | 304 ± 91.6 | 30 ± 40.3 | 0.00 ± 0.0 | 0.00 ± 0.0 | 0.00 ± 0.0 | 14 ± 11.5 |
| agents | 0.00 ± 0.0 | 2.91 ± 2.4 | 0.50 ± 0.7 | 57 ± 8.5 | 11 ± 3.5 | 304 ± 91.6 | 30 ± 40.3 | 0.00 ± 0.0 | 0.00 ± 0.0 | 0.00 ± 0.0 | 14 ± 11.5 |

### Normal demand · partial information

| policy | deaths | outcome_score | critical_on_time | critical_care_mean | response_mean | overload_min | er_wait_over_base | not_in_care_end | capacity_failures | escalations | llm_calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nearest | 0.00 ± 0.0 | 2.81 ± 2.3 | 0.00 ± 0.0 | 84 ± 23.3 | 9.62 ± 2.1 | 316 ± 97.3 | 37 ± 53.3 | 0.00 ± 0.0 | 0.80 ± 1.1 | 0.00 ± 0.0 | 0.00 ± 0.0 |
| rule_based | 0.00 ± 0.0 | 2.88 ± 2.3 | 0.00 ± 0.0 | 68 ± 0.7 | 9.62 ± 2.1 | 311 ± 90.8 | 9.80 ± 21.4 | 0.00 ± 0.0 | 0.20 ± 0.4 | 0.00 ± 0.0 | 0.00 ± 0.0 |
| agents_no_negotiation | 0.00 ± 0.0 | 2.92 ± 2.4 | 1.00 ± 0.0 | 53 ± 5.7 | 11 ± 5.6 | 317 ± 90.7 | 12 ± 13.7 | 0.00 ± 0.0 | 0.20 ± 0.4 | 0.00 ± 0.0 | 16 ± 12.4 |
| agents | 0.00 ± 0.0 | 2.92 ± 2.4 | 1.00 ± 0.0 | 53 ± 5.7 | 11 ± 5.6 | 317 ± 90.7 | 12 ± 13.7 | 0.00 ± 0.0 | 0.20 ± 0.4 | 0.20 ± 0.4 | 18 ± 14.2 |

### Surge demand · complete information

| policy | deaths | outcome_score | critical_on_time | critical_care_mean | response_mean | overload_min | er_wait_over_base | not_in_care_end | capacity_failures | escalations | llm_calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nearest | 3.60 ± 3.9 | 29 ± 2.2 | 0.33 ± 0.0 | 62 ± 18.2 | 32 ± 24.9 | 644 ± 98.5 | 299 ± 61.5 | 8.00 ± 2.5 | 19 ± 2.5 | 2.80 ± 1.3 | 0.00 ± 0.0 |
| rule_based | 3.00 ± 2.5 | 31 ± 2.1 | 0.33 ± 0.0 | 67 ± 15.0 | 46 ± 20.0 | 709 ± 93.9 | 548 ± 164.6 | 5.60 ± 2.5 | 10 ± 3.2 | 4.40 ± 2.6 | 0.00 ± 0.0 |
| agents_no_negotiation | 3.40 ± 3.5 | 30 ± 2.0 | 0.33 ± 0.0 | 69 ± 19.9 | 56 ± 23.8 | 696 ± 117.9 | 540 ± 130.2 | 5.60 ± 2.1 | 12 ± 1.8 | 4.20 ± 2.9 | 73 ± 24.0 |
| agents | 3.40 ± 2.6 | 30 ± 1.5 | 0.33 ± 0.0 | 66 ± 18.2 | 48 ± 28.4 | 705 ± 132.2 | 517 ± 136.0 | 5.80 ± 3.7 | 12 ± 2.6 | 4.80 ± 3.1 | 126 ± 31.7 |

### Surge demand · partial information

| policy | deaths | outcome_score | critical_on_time | critical_care_mean | response_mean | overload_min | er_wait_over_base | not_in_care_end | capacity_failures | escalations | llm_calls |
|---|---|---|---|---|---|---|---|---|---|---|---|
| nearest | 3.80 ± 3.1 | 29 ± 2.4 | 0.37 ± 0.2 | 63 ± 16.6 | 25 ± 22.6 | 620 ± 117.9 | 288 ± 80.9 | 8.40 ± 2.5 | 20 ± 5.3 | 3.20 ± 1.5 | 0.00 ± 0.0 |
| rule_based | 3.60 ± 3.1 | 30 ± 2.2 | 0.37 ± 0.2 | 63 ± 16.1 | 48 ± 21.7 | 707 ± 116.4 | 536 ± 131.4 | 6.20 ± 2.6 | 9.80 ± 2.7 | 4.40 ± 2.4 | 0.00 ± 0.0 |
| agents_no_negotiation | 3.60 ± 2.5 | 30 ± 2.2 | 0.36 ± 0.2 | 65 ± 16.1 | 62 ± 30.0 | 687 ± 103.4 | 558 ± 130.5 | 6.60 ± 1.9 | 11 ± 5.5 | 4.40 ± 2.9 | 69 ± 18.4 |
| agents | 4.00 ± 3.7 | 30 ± 2.5 | 0.36 ± 0.2 | 60 ± 16.5 | 70 ± 41.3 | 702 ± 115.1 | 504 ± 146.3 | 6.00 ± 3.4 | 13 ± 3.4 | 4.40 ± 2.9 | 117 ± 22.0 |

## Hypotheses

Paired comparisons on identical scenarios (same seed). With few seeds this is descriptive evidence, not a significance test.

**H1. Negotiation reduces unresolved conflicts and capacity-related failures** (agents vs agents without negotiation, all cells).
- Verdict: not supported
- capacity_failures: mean improvement -0.25 (lower is better); better in 3/20 paired runs, worse in 6
- overload_min: mean improvement -6.30 (lower is better); better in 3/20 paired runs, worse in 7

**H2. Negotiation improves time to definitive care for critical patients during scarcity** (surge cells).
- vs rule_based: verdict mixed; critical_care_mean: mean improvement +1.83 (lower is better); better in 6/10 paired runs, worse in 3; critical_on_time: mean improvement -0.01 (higher is better); better in 1/10 paired runs, worse in 1
- vs agents_no_negotiation: verdict mixed; critical_care_mean: mean improvement +3.70 (lower is better); better in 3/10 paired runs, worse in 5; critical_on_time: mean improvement +0.00 (higher is better); better in 0/10 paired runs, worse in 0

**H3. The benefit is larger under surge and partial information** (agents vs rule_based, outcome score).
- normal / complete: outcome_score: mean improvement +0.01 (higher is better); better in 2/5 paired runs, worse in 1
- normal / partial: outcome_score: mean improvement +0.04 (higher is better); better in 4/5 paired runs, worse in 0
- surge / complete: outcome_score: mean improvement -0.58 (higher is better); better in 2/5 paired runs, worse in 3
- surge / partial: outcome_score: mean improvement -0.63 (higher is better); better in 0/5 paired runs, worse in 5
- Verdict: not supported (surge gain -0.60 vs normal +0.03; partial gain -0.29 vs complete -0.29)

## Confidence calibration (agents)

| confidence bin | decisions | matched hindsight-best |
|---|---|---|
| 0.00-0.75 | 11 | 27% |
| 0.75-0.90 | 3 | 100% |
| 0.90-1.00 | 46 | 76% |

## Cost per run

| policy | LLM calls | tokens | wall seconds |
|---|---|---|---|
| nearest | 0 | 0 | 0.1 |
| rule_based | 0 | 0 | 0.1 |
| agents_no_negotiation | 43 | 89358 | 13.1 |
| agents | 69 | 143832 | 70.8 |
