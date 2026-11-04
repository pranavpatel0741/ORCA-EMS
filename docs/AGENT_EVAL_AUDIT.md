# Agent grounding and evaluation audit

Audit date: 2026-10-31. Scope: agent schemas, prompts, tools, orchestration, caching,
confidence, engine validation, all evaluation modules, and the archived experiment grid.
This audit used local code, event logs, recorded model answers, and offline tests. It did
not make new model calls or establish the truth of arbitrary model-written explanations.

> **Follow-up (2026-11-04):** the experiment grid was regenerated with the fixed code
> (`results/summary.md`, `docs/REPORT.md` §5). The pre-audit tables are in
> `results/archive/2026-10-31_before_audit/`.

## Conclusion

The archive has real structural problems; a passing test suite was not enough to establish
that model answers and evaluation claims were grounded. The confirmed issues below are fixed.
Historical tables remain preserved and explicitly labeled historical. They must be regenerated
before being presented as results for the revised implementation.

## Findings and fixes

| Finding | Why it matters | Change |
| --- | --- | --- |
| Typed answers lacked contextual grounding checks | A valid schema could still name another hospital/call or invent a patient | Validate observed IDs, hospital identity, proposal membership, duplicate patient IDs, allocator scope, and scene-report counts before using an answer |
| Negative estimated counts and nonpositive mutual-aid requests were accepted by output schemas | Structurally valid output could contain impossible quantities | Nonnegative count bounds and positive mutual-aid units |
| Four cached assessment answers contradict supplied scene counts | These are concrete structured factual errors, beyond subjective rationale wording | Current grounding rejects these answers and retries/falls back; usage records mark failed grounding |
| Staff-lender selection used other hospitals' live nurse data | This crossed the stated partial-information boundary | Candidate selection uses the shared status board; the chosen hospital answers about its own staffing |
| Stabilization-only admissions were removed from the critical-patient denominator and included in care-time averages | Reported definitive-care success could be overstated | Retain all critical patients in the denominator, exclude stabilization from definitive-care times, and count surviving stabilization-only patients as still awaiting definitive care |
| Hindsight comparator included a chosen hospital even when not fully capable | A stabilization destination could be rewarded as the best definitive-care choice | Compare only fully capable hospitals |
| AI/rule provenance depended on the rationale's text prefix | Model wording could change source attribution | Explicit program-owned decision-source fields |
| Saved scripted-run scorecards counted agent decisions under an AI heading | A dry run could appear to be real-model evidence | Scripted decisions have a separate count and explicit stand-in label |
| Reports could pool different backends or duplicate cells | Scripted outputs or repeated seeds could distort an LLM comparison | Reject mixed agent backends, duplicate cells, and mixed recorded fingerprints within a policy |
| Existing experiment files were reused without checking current code | Changed policies/metrics could silently return old numbers | Code/prompt/model/calibration fingerprint and explicit `--rerun` for stale results |
| Confidence configuration suggested three consistency samples | Repeated allocator sampling is not implemented | Set/document the actual single-candidate behavior; describe the score as a heuristic, not a calibrated probability |

Grounding does not prove that a hospital's acceptance or a free-text rationale is factually
correct. The engine still validates capacity, capability, contracts, staffing, patient ownership,
and scene safety before committing actions. Forecasts and rationale claims remain fallible.

## Archive evidence

- **80/80** saved result files have associated event logs.
- **2,125** logged model calls reference **1,638** distinct cached answer files checked.
- No missing referenced answer files or cache-hash/model metadata mismatches were found in these
  checked calls. A matching cache demonstrates local provenance, not independent proof of a
  historical network interaction.
- No scripted-model calls were found in records labeled OpenAI.
- All **10** demand/seed scenario groups match across policies and information conditions.
- No committed action lacked a preceding matching logged validation. This is a log-consistency
  check; it is not an independent re-execution of every historical commit's safety predicates.
- **Four** agent-policy records have zero calls because their scenarios contain zero incidents.
  They are not API failures and should not be described as 40 nonempty LLM trials.
- **Six** result records differ when recomputed from their associated logs using corrected metrics:
  two stabilization cases and four other records with usage/log mismatches. One of those four
  also has a serious-patient care-time mismatch. The original cause of the stored/log divergence
  is not established by this audit.

Details: [machine-readable archive audit](../results/audit/agent_eval_audit.json).

## Current-code replay

All 80 experiment cells were attempted with current code, engine invariants at every tick,
and `cache_only` model access:

- **52 completed:** all 40 baseline cells and 12 agent-policy cells, including the four empty
  agent scenarios.
- **28 stopped with a missing required cached answer.** Stricter validation or changed
  decision paths require requests that were not previously recorded. These are incomplete
  replays, not successful current-code evaluations or demonstrated new model failures.
- No other execution failures occurred in this replay sweep.

The historical run files were not overwritten. See [per-cell replay details](../results/audit/current_code_replays.json).
The full regression suite, including adversarial grounding, provenance, information access,
and stabilization/hindsight cases, passes after the changes (**286 tests**).

## Before the presentation or a new research claim

1. Use the guided scripted walkthrough to demonstrate the workflow, with its source labels.
2. For current real-model results, provide a working API key and regenerate the grid explicitly:
   `LLM_MODE=record .venv/bin/python eval/run_experiments.py --seeds 5 --rerun`.
   This makes paid model calls and replaces the existing result cells; preserve an archive first.
3. Compare deaths and patients still awaiting care alongside care-time averages. Those averages
   include only patients who reached definitive care, so they can conceal worse outcomes for
   patients who never reached it.
4. Treat `capacity_failures` as a composite proxy (R2 rejection events plus patients awaiting care),
   not a number of distinct patients. Treat paired verdicts as descriptive, not statistical proof.
5. Do not claim “no hallucinations.” The defensible claim is that specific structured errors are
   detected, committed actions are checked, sources are labeled, and remaining limits are documented.
