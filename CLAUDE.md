# CLAUDE.md — Hiring Pipeline take-home

## What this is

A take-home assignment. `README.md` in this repo is the complete, authoritative
spec — read it in full before doing anything. `docs/*.md` are stub files you
must fill in with real information as you go (never invent their contents).
`SUBMISSION.md` is filled in at the very end.

The README's own words matter: "Several of the ten [goals] spell out exact
rules... those specifics are the actual ask, not just the bold headline in
front of them." Read each goal's full paragraph, not just its bold title.

## Non-negotiable rules

- **Do not add any technology, library, service, or dependency not already
  listed below without stopping and asking first.** Tell me what it is, why
  it's needed, and wait for approval. This includes small "obviously fine"
  packages — if it's not in the approved list, ask.
- **Never guess on anything the README doesn't specify.** Stop and ask. Do
  not silently pick an interpretation of an ambiguous rule.
- **All authorization and business rules are enforced server-side.** The
  frontend hiding a button is never sufficient. Every recruiter-only or
  interviewer-only action must be checked in the backend.
- Keep business logic in `app/services/`, not in route handlers.
- Every meaningful chunk of work ends with: tests passing, a focused git
  commit with a clear message, and a short report to me in the format at the
  bottom of this file. Don't batch multiple goals into one commit.
- Don't start stretch features. Finish the 10 README goals first.
- Don't fabricate test results, decisions, or git history. If something
  fails, say so and show the failure.

## Tech stack (approved — do not deviate)

**Backend:** Python 3.12, FastAPI, SQLAlchemy 2.0 (sync, not async — see
Decisions below), Alembic, PostgreSQL, PyJWT, bcrypt, pytest, httpx (for
FastAPI's TestClient), pydantic-settings, psycopg2-binary, uvicorn.

**Frontend:** React + Vite, Tailwind CSS v4 (via `@tailwindcss/vite`), Axios,
Recharts, react-router-dom.

Explicitly not used: Docker, Redis, Celery, GraphQL, Redux, Kubernetes,
microservices, third-party auth, any UI component library (Tailwind utility
classes only), passlib, python-jose, Faker/factory libraries for seed data
(hand-write realistic seed data instead).

## Repo layout

```
backend/
  app/
    main.py         FastAPI app, CORS, router registration
    config.py        pydantic-settings, reads .env
    database.py       SQLAlchemy engine/session/Base
    models.py         all ORM models — read this fully before adding fields
    auth.py            bcrypt hashing + JWT encode/decode
    deps.py             get_current_user, require_recruiter, require_interviewer
    routers/           one file per resource, thin — calls into services/
    services/           business logic lives here
    schemas/            pydantic request/response models, one file per resource
  alembic/              migrations — autogenerate, then read the diff before applying
  tests/                pytest, real Postgres test DB, one file per resource
  requirements.txt
  .env.example / .env  (.env is gitignored, never commit real secrets)
frontend/
  src/
    api/client.js        axios instance, JWT interceptor, 401 handling
    context/AuthContext.jsx
    components/          shared UI (Layout, ProtectedRoute, StageBadge, etc.)
    pages/                one file per route
    App.jsx                router
docs/                    plan.md / schema.md / architecture.md / decisions.md / ai-prompts.md — fill in as you go, don't invent
```

## Already resolved decisions — do not re-litigate these

- **Sync SQLAlchemy, not async.** Simpler to explain in an interview; FastAPI
  runs sync routes in a threadpool, which is fine at this scale.
- **bcrypt + PyJWT directly**, no passlib or python-jose wrapper layers.
- **No `EmailStr`** — it needs the unapproved `email-validator` package. Use
  the plain-string + regex validator pattern already in `app/schemas/auth.py`.
- **Job opening `status` (open/closed) is separate from `archived` (bool).**
  Status describes whether the position is actively hiring; archived
  controls default-view visibility without deleting its applications.
- **Stalled-alert dismissal state lives as two columns directly on
  `Application`** (`stall_dismissed_at`, `stall_dismissed_stage`), not a
  separate table. A dismissal is only valid for the stage it was made at —
  if `current_stage` no longer matches `stall_dismissed_stage`, the
  dismissal is stale and the alert can reappear. That's the whole
  reappearance rule from goal 10, no extra logic needed.
- **CSV export's "every open application"** (goal 7) means every application
  NOT in a terminal stage (`current_stage` not in `{HIRED, REJECTED}`) —
  regardless of whether its job opening is open or archived. If you think
  this is wrong, ask before changing it, don't just reinterpret.
- **"Interviews scheduled this week"** dashboard KPI (goal 8): there is no
  interview date/time field anywhere in the spec (goal 3 explicitly closes
  the list of application fields), so this is calculated as: count of
  `ApplicationHistoryEntry` rows where `event_type = STAGE_CHANGE`,
  `new_stage = INTERVIEW`, and `created_at` falls in the current week. Do
  not add a scheduling field to solve this differently without asking first.
- **No public signup.** This is an internal tool — users exist only via the
  seed script. No registration UI or endpoint.
- **No backward stage moves** other than reject → reinstate-to-prior-stage.
  Advancing only ever moves one step forward in
  `Applied → Screening → Interview → Offer → Hired`.
- **Stalled alerts exclude terminal stages** (`Hired`, `Rejected`) — a hired
  or rejected candidate isn't "stalled," they're done.
- **The `ApplicationHistoryEntry` timeline is append-only by convention**
  (no code path anywhere issues UPDATE/DELETE against it), not enforced by a
  DB trigger. Keep it that way — don't add an ORM update/delete path to it.
- **Design direction (frontend):** functional internal tool, not a marketing
  page. System font stack (no external font loading — avoids adding a
  dependency on Google Fonts availability). A deliberate stage-color system
  (applied=slate, screening=blue, interview=violet, offer=amber, hired=green,
  rejected=brick red) used consistently everywhere a stage appears, as
  functional information, not decoration. Palette/tokens are in
  `frontend/src/index.css`'s `@theme` block — reuse those variables, don't
  introduce new ad hoc colors.
- **Deployment target (not yet done):** Render (backend) + Vercel (frontend)
  + Supabase (Postgres), per the README's suggested combo. I will do the
  actual account setup, GitHub push, and deploy clicks myself — your job is
  to produce correct config files (e.g. a `render.yaml` / build & start
  commands documented in a deploy doc) and leave connection details as env
  vars, never hardcoded.

## Current implementation state

**Done and tested (2 commits so far):**
- Postgres running locally; `hiring_pipeline` (dev) and `hiring_pipeline_test`
  databases exist. Connection details in `backend/.env.example`.
- Full data model in `backend/app/models.py`: `User`, `JobOpening`,
  `Application`, `ApplicationInterviewer` (join table), `ApplicationHistoryEntry`.
  Read this file fully before adding any new field or table — most of what
  you need for goals 2–10 already has a home here.
- Alembic initial migration applied.
- JWT login (`POST /auth/login`), `GET /auth/me`, bcrypt hashing, RBAC
  dependencies (`get_current_user`, `require_recruiter`, `require_interviewer`).
- Backend tests: `backend/tests/test_auth.py`, 7 passing. Test fixtures/factories
  in `backend/tests/conftest.py` — reuse `recruiter`, `interviewer`, `make_user`,
  `client`, `db_session`, `auth_headers` rather than rewriting setup per file.
- Frontend scaffolded: Tailwind v4 tokens, axios client with JWT interceptor,
  `AuthContext`, `ProtectedRoute`, sidebar `Layout` (role-based nav: recruiter
  sees Dashboard/Openings/Applications/Alerts, interviewer sees only "My
  Assignments").

**Not yet done:**
- Frontend `Login` page component and `App.jsx` router wiring (still the
  default Vite scaffold) — this blocks any end-to-end manual testing.
- No seed script yet.
- Everything past goal 1: job openings, applications, pipeline transitions,
  interview panel, search/filter/sort/pagination, bulk actions, CSV export,
  dashboard, history/timeline endpoints, stalled alerts.
- No deployment config yet.

## How to run things locally

```bash
# Postgres (adjust for your OS — this assumes it's already installed and running)
psql -U hiring_pipeline -d hiring_pipeline   # dev DB
psql -U hiring_pipeline -d hiring_pipeline_test  # test DB
# If these don't exist yet on your machine, create the role/DBs matching
# backend/.env.example's DATABASE_URL, or point DATABASE_URL at your own instance.

# Backend
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in a real DATABASE_URL and JWT_SECRET_KEY
alembic upgrade head
pytest -v
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev   # http://localhost:5173
```

## Report format — use this after every goal/session

```
## Goal N: <name> — status

**Implemented:** what actually works now
**Files created/modified:** list
**Tests run and results:** exact pytest output summary (pass/fail counts), any frontend build check
**Decisions made:** what you chose, what alternative you considered, why (I'll turn real ones into docs/decisions.md)
**Mistakes/problems hit:** what went wrong and how you fixed it (goes in docs/ai-prompts.md)
**Still incomplete / deferred:** anything from this goal not finished, and why
```
