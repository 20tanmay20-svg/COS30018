# COS30018 - Intelligent Systems Project

An agentic AI system that turns a clinician's request into a clinician-review report for glioblastoma (GBM) patients. It is built two ways so they
can be compared:

- **Multi-agent system**: five agents (patient info, medical evidence, clinical decision
  support, verification, report) that pass a shared state along a pipeline.
- **Single-agent system**: one agent that does the same phases with one set of tools.
- **Frontend**: a React web app (Vite + TypeScript).

Both agent systems read patients from `agent_system/data/processed/gbm_patient_profiles.json`,
search PubMed for evidence, and produce a Markdown report. Reports are drafts for clinician
review and are not medical advice.

---

## Project structure

```text
COS30018/
├── agent_system/
│   ├── multi_agent/      # Multi-agent pipeline (main.py), its tests and evaluation
│   ├── single_agent/     # Single-agent pipeline (run_single_agent.py) and its tests
│   ├── tools/            # Tools shared by both systems
│   ├── data/             # Raw clinical spreadsheet and processed patient profiles
│   ├── data_processing/  # Script that builds the processed profiles
│   └── requirements.txt  # Python packages for both agent systems
├── backend/              # FastAPI routes and services used by the web app
├── frontend/             # React web app
├── tests/                # Unit tests for the agents and tools
└── .env                  # Your API key (not committed, see Setup)
```

---

## Setup (once)

You need Python 3.10 or newer, and Node.js 18 or newer for the frontend.

**1. Create a virtual environment and install packages**

macOS / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r agent_system/requirements.txt
```

Windows (PowerShell):
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r agent_system/requirements.txt
```

**2. Add your Gemini API key**

Create a file named `.env` in the project root (the `COS30018` folder):

```text
GEMINI_API_KEY=your-key-here
GEMINI_MODEL=gemini/gemini-2.5-flash
```

The free tier allows about 15 requests per minute, so a full run can hit rate limits.
To use a local model instead, set `MODEL_PROVIDER=ollama` and `LOCAL_MODEL=ollama/qwen2.5:7b`
(Ollama must be running).

---

## Multi-agent system

Run from the `multi_agent` folder.

macOS / Linux:
```bash
cd agent_system/multi_agent
python3 main.py
```

Windows (PowerShell):
```powershell
cd agent_system\multi_agent
python main.py
```

At the `User Request:` prompt, type a request, for example
`Prepare a report for PatientID_0003`. A follow-up that does not name a patient, such as
`remove medication recommendations`, revises the current report. Type `exit` to quit.

**What a run saves** (in `agent_system/multi_agent/reports/`): the report (`.md`, when one is
produced), a summary (`.json`: time, tokens, cost, tool calls, stages) and a log (`.log`).

**Evaluation cases.** Start a request with a case ID to run it as one of the ten evaluation
cases, for example `CMP-05: Prepare a report for PatientID_0003`. Cases CMP-05 to CMP-08 add a
fault on purpose (unsupported claim, bad citation, conflicting history, failed evidence search).
Then score all saved runs:

macOS / Linux:
```bash
python3 test_pipeline/evaluate_runs.py
```

Windows (PowerShell):
```powershell
python test_pipeline\evaluate_runs.py
```

The result is written to `agent_system/multi_agent/test_pipeline/results/`.

**Unit tests**  Run from the project root. They run offline in about a second, 
using a scripted stand-in for the model. Set `LIVE=1` to use the real model.

macOS / Linux:
```bash
python3 -m pytest agent_system/multi_agent/test_agents -v
LIVE=1 python3 -m pytest agent_system/multi_agent/test_agents -v
```

Windows (PowerShell):
```powershell
python -m pytest agent_system\multi_agent\test_agents -v
$env:LIVE=1; python -m pytest agent_system\multi_agent\test_agents -v
```

---

## Single-agent system

The single agent reads `GEMINI_MODEL_ID` (not `GEMINI_MODEL`), so create
`agent_system/.env` with:

```text
GEMINI_API_KEY=your-key-here
GEMINI_MODEL_ID=gemini-2.5-flash
```

Run from the project root. Add `--report-output report.md` to save the report to a file.

macOS / Linux:
```bash
python3 agent_system/single_agent/run_single_agent.py
```

Windows (PowerShell):
```powershell
python agent_system\single_agent\run_single_agent.py
```

At the prompt, type a request. Pressing Enter with nothing typed uses
`make me a report for patient 7`. The full pipeline state is printed as JSON.

Tests for the single agent are in `agent_system/single_agent/tests/`.

---

## Frontend

macOS / Linux and Windows:
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. The dev server forwards `/api` requests to the backend at
`http://127.0.0.1:8000`, so the backend must be running for the app to show data.

---

## Backend

The web app talks to the FastAPI routes in `backend/app/`. Install its packages with
`pip install -r backend/requirements.txt`.



---

## Tests for the whole project

Run from the project root.

macOS / Linux:
```bash
python3 -m pytest tests -v
```

Windows (PowerShell):
```powershell
python -m pytest tests -v
```
