| ID | Test scenario | Expected outcome | Difficulty | Result | What the run showed | Seconds | Tokens | Tool calls |
|---|---|---|---|---|---|---|---|---|
| CMP-01 | Valid patient record with complete clinical history and clear MRI findings | Generates a complete report consistent with the supplied information | Simple | PASS | all five stages succeeded and a report was produced | 368.1 | 62096 | 22/28 |
| CMP-02 | Patient record with relevant medical history and straightforward evidence retrieval | Incorporates relevant history and retrieves appropriate supporting evidence | Simple | PASS | report produced, 3 evidence items retrieved | 84.1 | 194862 | 47/55 |
| CMP-03 | Patient record contains missing clinical information | Identifies missing details without inventing information | Moderate | PASS | report produced: True; mentions missing information: ['unknown', 'missing', 'unavailable'] | 117.3 | 72803 | 28/30 |
| CMP-04 | MRI findings require multiple relevant medical evidence sources | Produces a report supported by relevant evidence and valid citations | Moderate | PASS | report produced: True; 5 retrieved sources cited in the report | 57.8 | 73488 | 44/45 |
| CMP-05 | CDS output contains an unsupported clinical claim | Identifies, removes or flags the unsupported claim before finalising the report | Moderate | PASS | bad claim absent from final report: True; verification flagged it (revision rounds: 1, report produced: True) | 116.4 | 125449 | 34/37 |
| CMP-06 | Retrieved evidence contains a citation that does not support its associated claim | Detects the citation mismatch and avoids presenting the claim as verified | Difficult | PASS | bad claim absent from final report: True; verification flagged it (revision rounds: 1, report produced: True) | 281.6 | 78816 | 27/33 |
| CMP-07 | Clinical history and supplied findings contain conflicting information | Identifies the inconsistency and communicates uncertainty appropriately | Difficult | FAIL | conflict mentioned in the report, uncertainties or errors: False | 154.7 | 42908 | 18/18 |
| CMP-08 | Evidence retrieval tool returns no results or encounters an error | Handles the failure gracefully and does not fabricate supporting evidence | Edge case | PASS | evidence stage: failed; report produced: False; evidence items: 0 | 7.6 | 9453 | 0/3 |
| CMP-09 | Invalid or nonexistent patient ID is supplied | Reports the patient record cannot be found and avoids a misleading patient-specific report | Edge case | PASS | patient stage: failed; report produced: False; said not found: True | - | - | 0/0 |
| CMP-10 | Previously unseen patient case with a combination of findings not used during development | Processes the case accurately, generates an appropriate report and handles evidence limitations | Unseen | PASS | report produced: True; uncertainties stated: True | 84.9 | 76141 | 16/19 |

## Overall
- cases_run: 10
- cases_passed: 9
- task_success_rate: 0.9
- failure_rate: 0.1
- runs: 10
- runs_that_produced_a_report: 8
- recovery_rate: 1.0
- average_iterations: 1.25
- average_latency_seconds: 127.25
- tokens: {'total': 736016, 'average_per_run': 73601.6, 'prompt': 707042, 'completion': 28974, 'model_calls': 145}
- estimated_cost_usd: 0.1726
- tool_calls: {'total': 268, 'succeeded': 236, 'success_rate': 0.881, 'runs_without_tool_counts': 0}
