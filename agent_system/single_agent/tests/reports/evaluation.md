| ID | Test scenario | Expected outcome | Difficulty | Result | What the run showed | Seconds | Tokens | Tool calls |
|---|---|---|---|---|---|---|---|---|
| CMP-01 | Valid patient record with complete clinical history and clear MRI findings | Generates a complete report consistent with the supplied information | Simple | PASS | all five stages succeeded and a report was produced | 32.38 | n/a | n/a |
| CMP-02 | Patient record with relevant medical history and straightforward evidence retrieval | Incorporates relevant history and retrieves appropriate supporting evidence | Simple | PASS | report produced, 5 evidence items retrieved | 249.86 | n/a | n/a |
| CMP-03 | Patient record contains missing clinical information | Identifies missing details without inventing information | Moderate | PASS | report produced: True; mentions missing information: ['unknown', 'not provided'] | 50.01 | n/a | n/a |
| CMP-04 | MRI findings require multiple relevant medical evidence sources | Produces a report supported by relevant evidence and valid citations | Moderate | PASS | report produced: True; 4 retrieved sources cited in the report | 52.65 | n/a | n/a |
| CMP-05 | CDS output contains an unsupported clinical claim | Identifies, removes or flags the unsupported claim before finalising the report | Moderate | PASS | bad claim absent from final report: True; verification flagged it (revision rounds: 1, report produced: True) | 335.79 | n/a | n/a |
| CMP-06 | Retrieved evidence contains a citation that does not support its associated claim | Detects the citation mismatch and avoids presenting the claim as verified | Difficult | PASS | bad claim absent from final report: True; verification flagged it (revision rounds: 1, report produced: True) | 38.15 | n/a | n/a |
| CMP-07 | Clinical history and supplied findings contain conflicting information | Identifies the inconsistency and communicates uncertainty appropriately | Difficult | FAIL | conflict mentioned in the report, uncertainties or errors: False | 239.29 | n/a | n/a |
| CMP-08 | Evidence retrieval tool returns no results or encounters an error | Handles the failure gracefully and does not fabricate supporting evidence | Edge case | PASS | evidence stage: failed; report produced: False; evidence items: 0 | 20.5 | n/a | n/a |
| CMP-09 | Invalid or nonexistent patient ID is supplied | Reports the patient record cannot be found and avoids a misleading patient-specific report | Edge case | PASS | patient stage: failed; report produced: False; said not found: True | 0.0 | n/a | n/a |
| CMP-10 | Previously unseen patient case with a combination of findings not used during development | Processes the case accurately, generates an appropriate report and handles evidence limitations | Unseen | PASS | report produced: True; uncertainties stated: True | 41.3 | n/a | n/a |

## Overall
- cases_run: 10
- cases_passed: 9
- task_success_rate: 0.9
- failure_rate: 0.1
- runs: 10
- runs_that_produced_a_report: 8
- recovery_rate: 1.0
- average_iterations: 1.2
- average_latency_seconds: 105.99
- tokens: {'total': None, 'average_per_run': None, 'prompt': None, 'completion': None, 'model_calls': None}
- estimated_cost_usd: None
- tool_calls: {'total': None, 'succeeded': None, 'success_rate': None, 'runs_without_tool_counts': 10}
