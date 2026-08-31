# Submission

Fill this in and commit it. This is the first file we open.

## Links

- **GitHub repository:** https://github.com/sumitgurjar0509/takehome-03-hiring-pipeline
- **Live application:** https://takehome-03-hiring-pipeline.vercel.app

## Notes for the reviewer

The backend (Render free tier) and database (Supabase free tier) can both sleep after a period of
inactivity — the first request after that can take up to a minute or more to wake up, so a slow
first load is not a broken deployment. The frontend calls the backend API directly at
https://hiring-pipeline-api.onrender.com.

## Demo credentials

| Role | Email | Password |
|------|-------|----------|
| recruiter | recruiter@demo.com | RecruiterPass123! |
| recruiter | recruiter2@demo.com | RecruiterPass123! |
| interviewer | interviewer@demo.com | InterviewerPass123! |
| interviewer | interviewer2@demo.com | InterviewerPass123! |

## Stack

| Layer | What you used | Why |
|-------|---------------|-----|
| Frontend | React 19 + Vite, Tailwind CSS v4 (utility classes only, no component library), Axios, Recharts, react-router-dom | Fast dev loop, no build-tool fights; Tailwind's `@theme` tokens gave one place to define the stage-color system used consistently everywhere; Recharts for the one dashboard chart without hand-rolling SVG |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 (sync), Alembic, PyJWT + bcrypt (used directly, no passlib/python-jose wrapper) | FastAPI's dependency-injection model made server-side role enforcement (`require_recruiter`/`require_interviewer`) a one-line addition per route rather than something to remember by hand; sync SQLAlchemy is simpler to reason about and explain, and FastAPI runs sync routes in a threadpool anyway at this scale |
| Database | PostgreSQL | Native enum types for role/stage/status/event_type (invalid values rejected at the DB layer, not just in application code), real foreign keys, and a composite primary key on the interviewer-panel join table doing actual uniqueness enforcement |
| Hosting | Supabase (Postgres) + Render (backend API) + Vercel (frontend static build) | Free tiers on all three, matching the README's suggested combo; kept the three concerns (data, API, static assets) on three independently-deployable services rather than one box |

## Goal checklist

Mark each honestly. Partial is fine — say what is partial.

| # | Goal | Status | Notes |
|---|------|--------|-------|
| 1 | Accounts and roles | Done | JWT bearer auth, bcrypt password hashing, role checked server-side via a FastAPI dependency (`require_recruiter`/`require_interviewer`) on every route, not just hidden in the UI. No public signup — accounts exist only via the seed script. |
| 2 | Job openings | Done | Archive/restore are dedicated action endpoints, kept separate from `status` (open/closed) per the resolved decision that they mean different things. |
| 3 | Applications inside job openings | Done | Creating an application writes its `CREATED` history entry in the same transaction as the insert. |
| 4 | A pipeline with rules | Done | Illegal moves (skips, wrong direction, moves on a terminal stage) are rejected with a 409 and a specific reason. Hired is treated as terminal for reject too, not just Rejected — a deliberate call on an ambiguous reading of "reject from any stage" (docs/decisions.md #8). |
| 5 | Interview panel | Done | Many-to-many via a join table (`application_interviewers`); only interviewer-role users can be assigned, enforced server-side. |
| 6 | Finding candidates | Done | Search/filter/sort/pagination all happen in the SQL query, not client-side. Search is a plain `ILIKE`, not a dedicated search index — see docs/schema.md's "what breaks at 100x." |
| 7 | Acting on many candidates at once | Done | Bulk advance/reject reuse the exact goal 4 pipeline functions per application; one ineligible application in a batch never fails the others. CSV export excludes Hired/Rejected only, regardless of job opening status. |
| 8 | A dashboard | Done | One caught-and-fixed mid-session bug worth naming: `open_positions` initially counted archived-but-open openings too; caught, fixed, and the test extended to cover it (docs/decisions.md #23). |
| 9 | History you cannot rewrite | Done | Append-only by convention rather than a DB trigger — verified by grepping the whole codebase for any `UPDATE`/`DELETE` path against the history table; none exists. That's a real (accepted) gap, not a database-enforced guarantee — noted in docs/schema.md. |
| 10 | Stalled-application alerts | Done | The reappearance rule is a pure query-time comparison (`stall_dismissed_stage != current_stage`), no extra state added. The trickiest case — reject then reinstate back into a previously-dismissed stage — is specifically tested and seeded as a visible demo scenario, not just asserted in isolation. |

## How much time did you actually spend?

Under 15 hours total, against a beforehand estimate of 20–21 hours.

## What would you do next, with another 12 hours?

**TODO — fill in yourself.** (Personal judgment call — not generated.)

## What are you least happy with in this codebase, and why?

**TODO — fill in yourself.** (Personal judgment call — not generated.)
