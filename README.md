# COS30018 - Intelligent Systems Project

Full-stack medical AI application featuring:
- **Frontend**: React (Vite + TypeScript)
- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL
- **AI / Deep Learning**:
  - MONAI + PyTorch (BraTS SegResNet 3D Brain Tumor Segmentation)
  - smolagents (Hugging Face Clinical Tool-Calling Agent)
  - Google Gemini (Clinical text interpretation & structured radiology report generation)

---

## Project Structure

```text
COS30018/
├── backend/                  # FastAPI Backend & AI Services
│   ├── app/
│   │   ├── api/              # API routes
│   │   │   ├── __init__.py
│   │   │   └── routes.py     # Endpoints for health, MRI, agent, and reports
│   │   ├── core/             # Configuration & Database setup
│   │   │   ├── __init__.py
│   │   │   ├── config.py     # Environment settings
│   │   │   └── database.py   # PostgreSQL connection (SQLAlchemy)
│   │   ├── models/           # SQLAlchemy ORM models
│   │   │   ├── __init__.py
│   │   │   └── models.py     # Tables (scans, reports, chat)
│   │   ├── schemas/          # Pydantic schemas (request/response validation)
│   │   │   ├── __init__.py
│   │   │   └── schemas.py
│   │   ├── services/         # Business logic & AI frameworks
│   │   │   ├── __init__.py
│   │   │   ├── agent.py      # smolagents clinical reasoning agent
│   │   │   ├── gemini.py     # Google Gemini report generation & clinical text
│   │   │   └── mri.py        # MONAI SegResNet BraTS inference
│   │   ├── __init__.py
│   │   └── main.py           # FastAPI entry point
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                 # React Frontend (Vite + TypeScript)
│   ├── src/
│   │   ├── components/       # UI Components
│   │   ├── pages/            # App Views
│   │   ├── services/         # Axios / Fetch client to FastAPI
│   │   │   └── api.ts
│   │   ├── App.tsx           # Main component
│   │   ├── main.tsx          # React DOM entrypoint
│   │   └── index.css
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── Dockerfile
│
├── docker-compose.yml        # PostgreSQL, FastAPI, React orchestration
├── .gitignore
└── README.md
```

---

## Quickstart

### Option 1: Run with Docker Compose (Recommended)
```bash
docker-compose up --build
```
- Frontend: http://localhost:5173
- Backend API Docs (Swagger): http://localhost:8000/docs
- PostgreSQL: `localhost:5432`

### Option 2: Run Locally

#### 1. Backend
```bash
cd backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000
```

#### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
