# Agent tests

Controlled component tests for four agents, 30 cases in total.
Each case corresponds to one row of the test plan; some cases
include multiple checks.

- `test_patient_info.py`: PI-01 to PI-06
- `test_verification.py`: VA-01 to VA-08
- `test_medical_evidence.py`: ME-01 to ME-08
- `test_report_generation.py`: RG-01 to RG-08

## Run

Run from the repository root:

```bash
python3 -m pytest agent_system/multi_agent/test_agents -v
```

## Test configuration

By default, the Verification Agent uses a scripted stand-in judge
from `fake_models.py`. Set `LIVE=1` to use its configured real model.
This requires model configuration and may consume API quota.

The Medical Evidence tests always use controlled search results
and scripted assessments. The Report Generation tests always use
synthetic upstream states and deterministic assembly without an LLM.
These two suites remain offline even when `LIVE=1`.

These tests assess software behaviour, validation, and error handling.
They do not establish clinical accuracy or real-model relevance judgement.
Cases ME-08 and RG-08 should only be described as unseen if their inputs
were held out from development.

## Results

Results are written inside `test_agents/results/`:

- `patient_info.json`
- `verification.json`
- `medical_evidence.json`
- `report_generation.json`

Each file includes case outcomes and summary metrics. Timing, token
usage, and estimated cost are included where supported by the recorder.

The current `mode` field reflects the global `LIVE` setting.
It does not indicate live execution for Medical Evidence or Report
Generation, which always use controlled offline tests.

These 30 component cases are separate from the end-to-end evaluation
and single-agent versus multi-agent comparison.