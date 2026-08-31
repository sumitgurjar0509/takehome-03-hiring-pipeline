# Deployment

Free-tier combo per the README's suggestion: **Supabase** (Postgres) ->
**Render** (backend API) -> **Vercel** (frontend). Deploy in that order —
each later step needs a URL or connection string from the one before it.
This doc is config and reference only; the actual account setup, GitHub
push, and deploy clicks are done manually, not by this doc.

## 1. Database — Supabase

1. Create a new Supabase project. Note the Postgres connection string from
   Project Settings -> Database -> Connection string (use the "URI" /
   direct-connection form, not the pooler form, since Alembic runs DDL).
2. Supabase's connection string starts `postgresql://`. SQLAlchemy needs
   the psycopg2 driver named explicitly, so change the scheme to
   `postgresql+psycopg2://` before using it anywhere — same format as
   `backend/.env.example`'s local example.
3. Nothing else to do here — Alembic (chained into the backend's start
   command, below) creates the schema the first time the service boots.

## 2. Backend — Render

`render.yaml` at the repo root is a Blueprint — in the Render dashboard,
"New +" -> "Blueprint", point it at this repo, and it reads that file
automatically. It defines one Web Service:

| Setting | Value |
|---|---|
| Root directory | `backend` |
| Build command | `pip install -r requirements.txt` |
| Start command | `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Plan | Free |

Render's `preDeployCommand` isn't available on the free plan (confirmed
against the actual dashboard), so the migration is chained into the start
command instead — it runs on every process start/restart rather than
once per deploy. That's fine: `alembic upgrade head` is a no-op once the
database is already at head.

If you'd rather configure the service by hand instead of via Blueprint,
those three settings are all you need to enter.

**Python version: this service must run Python 3.12** (matching CLAUDE.md
and the local venv everywhere else) — not whatever Render defaults to.
Render's own default for services created since Feb 2026 is Python 3.14,
and SQLAlchemy 2.0.36 breaks under 3.13+'s typing internals for
annotated `mapped_column()` types (`TypeError: descriptor '__getitem__'
requires a 'typing.Union' object but received a 'tuple'`, raised from
SQLAlchemy's `de_stringify_union_elements`). The Blueprint pins this via
a `PYTHON_VERSION=3.12.14` env var rather than a `.python-version` file,
because Render only honors that file at the repo root, not inside a
`rootDir` subfolder like this service's `backend/` — the env var applies
regardless of `rootDir`. If configuring by hand instead of via Blueprint,
set `PYTHON_VERSION=3.12.14` in the service's environment variables.

**Environment variables** (Render dashboard -> service -> Environment; the
Blueprint declares these but the secret-shaped ones need a real value
pasted in manually):

| Variable | Where it comes from |
|---|---|
| `PYTHON_VERSION` | Fixed at `3.12.14` (in the Blueprint already) — see above. |
| `DATABASE_URL` | The Supabase connection string from step 1, with `+psycopg2` added. Set manually — never committed. |
| `JWT_SECRET_KEY` | Render generates and stores a random value automatically (`generateValue: true` in the Blueprint) — nothing to do. |
| `JWT_ALGORITHM` | Fixed at `HS256` (in the Blueprint already). |
| `JWT_EXPIRE_MINUTES` | Fixed at `480` (in the Blueprint already). |
| `CORS_ORIGINS` | The deployed Vercel URL, e.g. `https://hiring-pipeline.vercel.app`. Set manually once that URL exists — comma-separate if there's more than one (e.g. a production URL and a preview URL). |

Once deployed, note the Render service's public URL
(`https://<service-name>.onrender.com`) — the frontend needs it next.

**After the backend is live, seed it once:** Render's dashboard has a
"Shell" tab for a running service — open it and run `python -m app.seed`
to create the demo users and sample data (same script used locally). Do
this after the first successful deploy, not before.

## 3. Frontend — Vercel

Vercel's zero-config Vite preset handles the build; the only thing to set
explicitly is the root directory, since the frontend lives in a subfolder
of the repo.

| Setting | Value |
|---|---|
| Root directory | `frontend` |
| Framework preset | Vite (auto-detected) |
| Build command | `npm run build` (Vercel default for the Vite preset) |
| Output directory | `dist` (Vercel default for the Vite preset) |
| Install command | `npm install` (Vercel default) |

**Environment variable** (Vercel dashboard -> project -> Settings ->
Environment Variables):

| Variable | Value |
|---|---|
| `VITE_API_URL` | The Render backend URL from step 2, e.g. `https://hiring-pipeline-api.onrender.com` — no trailing slash. |

Vite only bakes `VITE_`-prefixed vars into the client bundle at build
time, so this must be set *before* the first deploy build, not added
afterward — if it's added later, trigger a redeploy to pick it up.

## Free-tier cold starts

Both Render's and Supabase's free tiers can sleep/pause after a period of
inactivity, and the first request after that can take upwards of a
minute while the service wakes back up. This is expected, not a broken
deployment — worth noting wherever the live URL is shared, so a slow
first load doesn't read as an outage.

## Local reference

`backend/.env.example` and `frontend/.env.example` list every variable
name each side needs (no real values) — copy to `.env` locally and fill
in. Neither `.env` file is committed (`.gitignore` covers both).
