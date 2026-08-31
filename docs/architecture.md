# Architecture

## What are the moving pieces, and how do they talk to each other?

Three pieces, talking in a straight line — browser to API to database, never
skipping a link:

- **A React single-page app** (Vite build). The only thing the browser ever
  runs. It talks to the backend exclusively over JSON/HTTPS via a single
  axios instance (`frontend/src/api/client.js`), attaching a JWT bearer
  token from `localStorage` to every request. There is no server-side
  rendering and no cookie-based session — every page reload re-derives
  "who am I" by calling `GET /auth/me` with the stored token.

- **A FastAPI backend**, one Python process, layered strictly:
  `routers/` (one file per resource, HTTP-shape only: parse the request,
  call a dependency for auth, call a service, return the response) ->
  `services/` (all business logic and every database query lives here —
  `applications.py`, `openings.py`, `panel.py`, `pipeline.py`,
  `dashboard.py`, `alerts.py`) -> `models.py` (the SQLAlchemy ORM layer).
  Nothing skips a layer: a router never touches SQLAlchemy directly, and
  role checks (`require_recruiter`/`require_interviewer` in `deps.py`) run
  as FastAPI dependencies before a router function body executes at all.

- **PostgreSQL.** The only stateful piece in the system. Both the frontend
  bundle and the backend process are stateless and can be redeployed or
  restarted with zero data-loss risk — all state that matters lives in one
  place.

Alembic isn't a running piece — it's a one-shot migration command
(`alembic upgrade head`). Locally, and in the backend's Render start
command, it runs immediately before `uvicorn` starts, on every process
boot, not as a separate deploy phase — `alembic upgrade head` is a no-op
once the database is already at head, so re-running it on every restart
is harmless. (Render's `preDeployCommand`, which would run it once per
deploy instead of once per boot, turned out not to be available on the
free plan — see `docs/deploy.md`.)

## Where does each piece run?

| Piece | Local dev | Production |
|---|---|---|
| Frontend | `vite dev` on `localhost:5173` | Static build (`vite build` -> `dist/`) served from Vercel's CDN — no Node process runs in production, just static files and client-side JS |
| Backend | `uvicorn --reload` on `localhost:8000` | A single `uvicorn` process on Render's native (non-Docker) Python runtime, bound to Render's assigned `$PORT` |
| Database | Local Postgres via Homebrew | Supabase-hosted Postgres, reached only by the backend over `DATABASE_URL` — the frontend never talks to the database directly, not even for reads |

The frontend and backend are two independently deployed things that only
know about each other through a URL: `VITE_API_URL` (baked into the
frontend build) and `CORS_ORIGINS` (told to the backend so it'll accept
requests from that URL). Full detail in `docs/deploy.md`.

## What is the request path for one representative user action, end to end?

**Applying a stage change** — a recruiter clicks "Advance to Screening" on
an application sitting in the Applied stage:

1. **Frontend, click handler** (`ApplicationForm.jsx`): `handleAdvance`
   computes the target stage from the current one (`nextStage()`, a
   frontend-side mirror of the backend's stage sequence, used only to
   label the button and pick what to send — it has no authority; the
   server re-derives and re-validates this independently) and calls
   `runPipelineAction(() => advanceApplication(id, target))`.
2. **Frontend, API client** (`api/applications.js`):
   `advanceApplication` does `api.post('/applications/{id}/advance', { to_stage: target })`.
   The axios request interceptor attaches `Authorization: Bearer <token>`
   from `localStorage` before the request leaves the browser.
3. **Network.** One HTTPS POST to the backend.
4. **Backend, auth dependency** (`deps.py`, runs before the route body):
   `require_recruiter` -> `get_current_user` decodes the JWT (PyJWT,
   verifies signature and expiry), loads the `User` row by the token's
   `sub` claim, and checks `role == RECRUITER`. Any failure here — no
   token, bad signature, expired, wrong role — short-circuits with a 401
   or 403 before any business logic runs.
5. **Backend, router** (`routers/applications.py::advance_application`):
   fetches the `Application` row (`applications_service.get_application_or_404`,
   a `SELECT ... WHERE id = :id`), then calls
   `pipeline_service.advance(application, payload.to_stage, current_user)`.
6. **Backend, service — the actual rule** (`services/pipeline.py::advance`):
   checks the application isn't Rejected or Hired, computes the one legal
   next stage (`next_stage_after`), and raises `PipelineError` (mapped to
   a 409 by the router) if the client's requested `to_stage` doesn't match
   it exactly. On success, it mutates the in-memory `Application` object
   (`current_stage`, `stage_changed_at = now()`, and clears
   `stall_dismissed_at`/`stall_dismissed_stage` — goal 10's reappearance
   rule depends on this happening here) and returns an unsaved
   `ApplicationHistoryEntry(STAGE_CHANGE, ...)`. Nothing has touched the
   database yet — this function only mutates Python objects.
7. **Backend, the actual write** (`_apply_transition` in the router):
   `db.add(history_entry)` then `db.commit()`. This is the one moment a
   SQL statement reaches Postgres: one `UPDATE applications SET
   current_stage = ..., stage_changed_at = ..., stall_dismissed_at = NULL,
   stall_dismissed_stage = NULL, updated_at = ... WHERE id = ...` and one
   `INSERT INTO application_history_entries (...)`, committed together in
   a single transaction — either both happen or neither does.
8. **Backend, response:** `db.refresh(application)` reloads the row
   (picking up the database's own `updated_at` trigger value), and
   FastAPI serializes it through the `ApplicationOut` Pydantic schema back
   to JSON.
9. **Frontend, back in `runPipelineAction`:** the resolved application
   replaces local state (the stage badge and button set re-render
   immediately), and a *second* request (`GET /applications/{id}/history`)
   fetches the refreshed timeline so the new `STAGE_CHANGE` entry appears
   without a full page reload.

Every other write in the app (reject, reinstate, feedback, bulk actions,
dismiss-alert) follows this same shape: router does auth + fetch, a
service function in `pipeline.py` or `applications.py` does the validation
and in-memory mutation, the router (or, for bulk actions, the service
function itself, since each item needs its own commit) does the actual
`db.add()`/`db.commit()`.

## What did you decide not to build, and why?

- **All nine README stretch ideas** (public careers page, structured
  scorecards, self-service scheduling links, a candidate-facing status
  portal, resume tagging/search, offer-letter generation, source-of-hire
  reporting, an email digest of stalled candidates, referral tracking) —
  none built. CLAUDE.md was explicit that the ten required goals were the
  entire scope; stretch work only starts after all ten are solid, and this
  submission's time went into the ten goals and their tests instead.
- **Real-time updates.** The stalled-alerts badge and dashboard numbers
  refresh on navigation and after relevant actions, not through a
  websocket or polling loop. Fine for one recruiter at a time; would start
  to matter with several recruiters actively working the same pipeline
  simultaneously and expecting to see each other's changes live.
- **A drag-and-drop pipeline board.** Stage changes are explicit button
  clicks (Advance / Reject / Reinstate), not a Kanban-style drag gesture.
  Partly this is simplicity, and partly deliberate: goal 4's illegal-move
  rejection needs to be the server's call, not something a drag
  interaction visually implies is fine before the server has confirmed it.
- **Any delete path for job openings or applications.** Archiving (goal 2)
  is the only "removal" concept in the system, matching the resolved
  decision that archiving hides without destroying. There is no code path
  anywhere that issues a `DELETE` against `job_openings` or `applications`.
- **Email of any kind.** No transactional email, no digest — goal 10's
  alerts are in-app only. "Email digest of stalled candidates" is
  explicitly one of the stretch ideas left undone.
- **Public signup.** Resolved out of scope early (CLAUDE.md) — this is an
  internal tool, and every account exists only via `backend/app/seed.py`.
- **Rate limiting or abuse protection** beyond JWT auth itself. Appropriate
  for an authenticated internal tool that was never going to be exposed to
  open internet traffic; would be a real gap for a public-facing product.
- **A UI component library.** Tailwind utility classes only, per the
  approved stack — no headless-UI/shadcn-style system, every control
  (buttons, badges, form fields) is hand-built.
- **A dedicated search index.** Goal 6's candidate search is a plain SQL
  `ILIKE '%term%'` — good enough at this data volume, but a leading
  wildcard can't use a standard btree index. See `docs/schema.md`'s "what
  breaks at 100x" for what would actually need to change here, and why it
  wasn't built now (it needs a dependency — `pg_trgm` or similar — outside
  the approved list).
- **Docker.** Explicitly excluded from the approved stack from the start;
  Render's native Python runtime and Vercel's native Vite preset are used
  as-is.
