# Agent tests

Unit tests for two agents, 14 cases in total. Each case is one row of the test plan.

- `test_patient_info.py`: PI-01 to PI-06
- `test_verification.py`: VA-01 to VA-08

Run from the repo root:

```bash
python3 -m pytest agent_system/multi_agent/test_agents -v
```

By default the tests run offline in about a second. The Verification agent gets a scripted
stand-in judge (`fake_models.py`) instead of the cloud model. Set `LIVE=1` to use the real model;
this needs the API key in `.env` and uses quota.

Results are written to `results/patient_info.json` and `results/verification.json`.
The `mode` field says whether a run was offline or live.
