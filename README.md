# DoctorBrief

**"Focus on the patient. Let DoctorBrief handle the documentation."**

DoctorBrief is a voice-first clinical documentation assistant built for doctors and small clinics in India. It lets clinicians record patient consultations (after explicit consent), transcribe audio with OpenAI Speech-to-Text (`gpt-transcribe`), extract structured clinical facts with strict anti-hallucination guardrails, draft SOAP notes, and review, edit, and approve documentation before saving it to patient history.

> **Disclaimer:** DoctorBrief is a clinical documentation assistant MVP, not a diagnostic system, autonomous prescriber, or certified medical device. All AI-generated drafts require review and approval by a licensed clinician.

---

## Features

- **Doctor Authentication & Multi-Tenant Isolation:** Registration, login, bcrypt password hashing, JWT authentication, and strict ownership checks so each doctor accesses only their own patients, consultations, and notes.
- **Clinic Dashboard:** Live database-backed metrics (total patients, total consultations, completed this month, notes awaiting approval), 7-day activity chart (Recharts), recent consultations, and quick actions.
- **Patient Management:** Auto-generated clinic patient IDs (`DB-0001`, ...), search/filter, editable demographics, medical history, allergies, and full approved clinical note history.
- **Voice Consultation Recording:** Explicit consent confirmation gate before enabling microphone access, browser MediaRecorder capture (WebM/Opus preferred), pause/resume/stop controls, live timer, playback preview, upload progress, and retry handling.
- **Speech-to-Text (`gpt-transcribe`):** Backend audio validation (empty file, MIME/extension, max size) and transcription via the official OpenAI Python SDK, preserving the unedited original transcript alongside doctor edits.
- **Clinical Fact Extraction & SOAP Generation:** Structured JSON extraction (`ClinicalExtractionPayload`) and SOAP drafting (`SoapNoteDraft`) that never invent vitals, symptoms, diagnoses, or prescriptions and explicitly flag missing information.
- **SOAP Note Editor & Versioned Approval:** `DRAFT → UNDER_REVIEW → APPROVED` workflow with transcript comparison, missing-info warnings, approval confirmation dialog, and immutable approved records (subsequent changes create a versioned amendment).

---

## Technology Stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, Radix/shadcn-style UI components, React Router, TanStack Query, React Hook Form + Zod, Lucide Icons, Recharts.
- **Backend:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, Alembic, PostgreSQL (`psycopg`), PyJWT, bcrypt.
- **AI & Speech Processing:** Official `openai` Python SDK (`gpt-transcribe` for audio transcription and structured-output chat completions for clinical extraction & SOAP drafting).
- **Deployment:** Vercel (frontend), Render (backend + managed PostgreSQL), Docker Compose (local Postgres).

---

## Project Structure

```text
doctorbrief/
├── frontend/
│   ├── src/
│   │   ├── components/       # UI primitives, layout, audio recorder, SOAP editor, patient cards
│   │   ├── contexts/         # AuthContext with persistent JWT session
│   │   ├── lib/              # Utility helpers & date/time formatting
│   │   ├── pages/            # All 13 application routes
│   │   ├── services/         # Typed API client
│   │   ├── test/             # Vitest + React Testing Library suite
│   │   └── types/            # TypeScript API models
│   ├── vercel.json
│   ├── package.json
│   └── .env.example
├── backend/
│   ├── app/
│   │   ├── ai/               # OpenAI transcription, extraction & SOAP prompts/client
│   │   ├── api/routes/       # Auth, dashboard, patients, consultations, notes endpoints
│   │   ├── database/         # SQLAlchemy engine & session management
│   │   ├── models/           # Doctor, Patient, Consultation, Transcript, Extraction, ClinicalNote
│   │   ├── schemas/          # Pydantic request/response & AI structured output schemas
│   │   ├── security/         # Password hashing, JWT helpers, auth dependency
│   │   ├── services/         # Business logic & ownership enforcement
│   │   ├── config.py
│   │   └── main.py
│   ├── migrations/           # Alembic migrations (001_initial_schema)
│   ├── tests/                # Pytest API & safety workflow suite
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── docker-compose.yml
├── render.yaml
└── README.md
```

---

## Local Setup

### 1. Start PostgreSQL (via Docker Compose or local Postgres)

```bash
docker compose up -d postgres
```

### 2. Configure and Run Backend

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` with your PostgreSQL URL, a strong `SECRET_KEY`, and your `OPENAI_API_KEY`:

```env
DATABASE_URL=postgresql+psycopg://doctorbrief:doctorbrief@localhost:5432/doctorbrief
OPENAI_API_KEY=sk-...
OPENAI_TRANSCRIBE_MODEL=gpt-transcribe
OPENAI_CLINICAL_MODEL=gpt-4o-mini
ALLOW_DEV_AI_MOCK=false
SECRET_KEY=replace-with-a-long-random-secret
ACCESS_TOKEN_EXPIRE_MINUTES=480
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
MAX_AUDIO_SIZE_MB=25
```

> **Local Testing Without an OpenAI Key:** Set `ALLOW_DEV_AI_MOCK=true` only in local development to use the clearly labelled `dev-mock` fallback adapter. Leave `ALLOW_DEV_AI_MOCK=false` in staging and production.

Run Alembic migrations and start FastAPI:

```bash
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### 3. Configure and Run Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open `http://localhost:5173`.

---

## Testing

### Backend Tests (Pytest)

External OpenAI calls are mocked in automated tests:

```bash
cd backend
pytest -v
```

### Frontend Tests & Production Build

```bash
cd frontend
npm test
npm run build
```

---

## Deployment

### Backend (Render)
1. Provision a Render PostgreSQL database and Web Service using `render.yaml` (or root directory `backend/`).
2. Build command: `pip install -r requirements.txt`
3. Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Set `DATABASE_URL`, `OPENAI_API_KEY`, `SECRET_KEY`, `CORS_ORIGINS` (your Vercel URL).

### Frontend (Vercel)
1. Import the `frontend/` directory in Vercel.
2. Build command: `npm run build`, Output directory: `dist`.
3. Set `VITE_API_BASE_URL` to your deployed Render backend URL.
4. `frontend/vercel.json` handles SPA client-side routing rewrites.

---

## Known Limitations

- Transcription processes completed audio recordings uploaded after stopping the microphone (not live streaming captions).
- Approved clinical notes are immutable; corrections require creating a new versioned amendment.
- Intended as a clinical documentation aid MVP; formal regulatory/HIPAA/DISHA compliance assessments are required before clinical production deployment.
