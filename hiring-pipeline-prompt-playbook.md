# Claude Code Prompt Playbook — Hiring Pipeline

One prompt block per Claude Code session. Copy a block in as-is (edit if your
own judgment differs), let it work, review the diff, run the tests, commit,
then paste that same prompt (and what you corrected, if anything) into rough
notes for `docs/ai-prompts.md` before moving to the next block. That last
step is not optional — it's graded, and it's much easier to capture right
after each session than to reconstruct at the end.

`CLAUDE.md` is already written and committed at the repo root — Claude Code
loads it automatically every session, so you never need to re-paste stack
rules or resolved decisions. Only the session-specific prompt below is
needed each time.

---

## The complete sequence, start to finish

Every action, in order, nothing skipped.

1. **Set up your machine** — Postgres, Python 3.12, Node, Claude Code. (§0 below)
2. **Unzip the progress zip** you already have, `cd` into
   `takehome-03-hiring-pipeline/`. It already has real git history (4
   commits), `CLAUDE.md`, and this playbook — no `git init` needed.
3. **Create the backend venv and install deps, `npm install` the frontend** —
   see `CLAUDE.md`'s "How to run things locally" section.
4. **Run `claude`** inside the project folder to start your first session.
5. **Run Session 0 (Resume + verify).** Read its report against `CLAUDE.md`
   and `README.md` yourself, especially its restated understanding of the
   pipeline state machine (goal 4) and the alert reappearance rule
   (goal 10). Don't approve on autopilot just because it sounds confident.
6. **Run Session 1 (finish goal 1).** Review diff → test → commit → note the
   prompt for `ai-prompts.md`.
7. **Run Session 2 (goal 2 — job openings).** Same loop.
8. **Run Session 3 (goal 3 — applications).** Same loop.
9. **Run Session 4 (goal 4 — pipeline rules).** Make it show you the
   transition table and rejection-message wording *before* it writes code —
   check that against README goal 4 first, then the same loop.
10. **Run Session 5 (goal 5 — interview panel).** Same loop.
11. **Run Session 6 (goal 6 — search/filter/sort/pagination).** Same loop.
12. **Run Session 7 (goal 7 — bulk actions + CSV export).** Same loop.
13. **Run Session 8 (goal 8 — dashboard).** Same loop.
14. **Run Session 9 (goal 9 — immutable timeline + feedback).** Same loop.
15. **Run Session 10 (goal 10 — stalled alerts).** Make it write out the
    reappearance logic in plain English *before* coding — check it against
    `CLAUDE.md`'s resolved decision first, then the same loop.
16. **Run Session 11 (review pass).** Full suite green, server-side
    enforcement double-checked. Commit any fixes.
17. **Run Session 12 (seed data + deployment config).** Review → test →
    commit.
18. **Actually deploy:** create your database (Supabase Postgres), deploy the
    backend (Render) with `DATABASE_URL`, `JWT_SECRET_KEY`, `CORS_ORIGINS`
    as environment variables — never in the repo — deploy the frontend
    (Vercel) with `VITE_API_URL` pointing at the Render URL, run
    `alembic upgrade head` against the production database, then open the
    live URL yourself and confirm login works with your seeded demo
    credentials.
19. **Run Session 13 (docs drafts)** for `architecture.md`, `schema.md`, and
    the stack table/goal checklist in `SUBMISSION.md`. Then edit every line
    yourself until you'd defend it on a call.
20. **Write `docs/decisions.md` yourself** — at least five real decisions
    from what actually happened in steps 6–17, including one you reversed.
    Your session reports and the resolved-decisions list in `CLAUDE.md` are
    raw material, not a document to copy-paste.
21. **Write `docs/plan.md` yourself** — how you actually split the work
    (compare against this playbook's suggested day-by-day pacing below),
    estimate vs. actual, what you cut.
22. **Write `docs/ai-prompts.md` yourself** — the prompts you actually typed
    (edit this playbook's text to match reality — note anywhere you deviated
    from a block), grouped by goal, including at least one that went wrong
    and what you did about it.
23. **Finish `SUBMISSION.md`** — repo and live URL, demo credentials for
    every role, the stack table, an honest per-goal status (partial is fine
    if you say so), time actually spent, and the closing questions.
24. **Final check:** open the live URL in a private browser window, log in
    with the demo credentials, confirm `.env` was never committed, confirm
    your git log shows real incremental history and not one giant commit.
25. **Submit:** push everything, then send the GitHub repo URL, the live
    URL, and confirm `SUBMISSION.md` is committed.

---

## 0. One-time machine setup

```bash
# --- macOS ---
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.12 node postgresql@16
brew services start postgresql@16

# --- Ubuntu/Debian (or WSL) ---
sudo apt update && sudo apt install -y python3.12 python3.12-venv nodejs npm postgresql postgresql-contrib
sudo service postgresql start

# Claude Code itself (same on both)
npm install -g @anthropic-ai/claude-code
```

> If the Claude Code install command has changed since early 2026, check
> docs.claude.com/en/docs/claude-code/overview — I can't verify it live.

Then create the local role/databases matching `backend/.env.example`'s
`DATABASE_URL` (or point it at your own Postgres instance):

```bash
psql postgres -c "CREATE USER hiring_pipeline WITH PASSWORD 'devpassword';"
psql postgres -c "CREATE DATABASE hiring_pipeline OWNER hiring_pipeline;"
psql postgres -c "CREATE DATABASE hiring_pipeline_test OWNER hiring_pipeline;"
psql postgres -c "ALTER USER hiring_pipeline CREATEDB;"
```

---

## Suggested day-by-day pacing (~12 hours / a week)

A guide, not a rule — log what you *actually* did for `docs/plan.md`'s
"estimated vs. actual" question. Session 4 and Session 10 are flagged
high-risk in `CLAUDE.md` for a reason; don't be surprised if either eats a
whole session on its own.

| Day | Sessions | Why grouped this way |
|-----|----------|------------------------|
| 1 | Session 0, Session 1 | Environment + finishing the auth/login loop is one coherent unit |
| 2 | Session 2, Session 3 | Openings and applications are both straightforward CRUD |
| 3 | Session 4 | Pipeline rules alone — highest-risk goal, give it room |
| 4 | Session 5, Session 6 | Panel assignment, then search/filter/sort/pagination |
| 5 | Session 7, Session 8 | Bulk actions + CSV, then dashboard (both lean on goal 4's history data) |
| 6 | Session 9, Session 10 | Timeline/feedback, then stalled alerts — second highest-risk goal |
| 7 | Session 11, 12, deploy, Session 13 | Review pass, seed data, actual deploy clicks, docs drafts — then you write decisions/plan/ai-prompts.md and SUBMISSION.md |

---

## Session 0 — Resume and verify

```
Read CLAUDE.md and README.md in full. Set up the local dev environment
(Postgres role/DBs, backend venv + deps, .env from .env.example, frontend
npm install) per CLAUDE.md's "How to run things locally" section. Run the
existing backend test suite and confirm all tests still pass.

Then, before touching any code, restate in your own words:
1. The full pipeline state machine from README goal 4 (every legal
   transition, and what happens on an illegal one).
2. The stalled-alert reappearance rule from README goal 10.
3. What's already built vs. not, per CLAUDE.md's "Current implementation
   state" section.

Do not write any new feature code yet. Report back using the report format
at the bottom of CLAUDE.md, with "Implemented" describing environment status
rather than a feature, and wait for me to confirm your restatement of goals
4 and 10 is correct before you're told to proceed to the next session.
```

---

## Session 1 — Goal 1: Accounts and roles (finish it)

```
Finish README goal 1. Backend auth (JWT login, bcrypt, RBAC dependencies) is
already done — read app/auth.py, app/deps.py, app/routers/auth.py before
touching anything. What's missing:

1. A seed script (backend/app/seed.py, run as `python -m app.seed`) that
   creates at least one recruiter and one interviewer demo user with known
   credentials. Print the credentials it created.
2. Frontend: a Login page (frontend/src/pages/Login.jsx) using AuthContext's
   login() — email/password form, error display on failed login. Wire it
   into App.jsx with react-router-dom: /login is public, everything else
   goes through ProtectedRoute. After login, redirect to "/".
3. A minimal placeholder home page at "/" so the login redirect has
   somewhere to land (it becomes the real dashboard in goal 8 — don't build
   dashboard content now, just enough to prove the login flow works).

Verify end-to-end manually: run both dev servers, log in as each seeded
role, confirm the sidebar nav differs by role (per Layout.jsx's existing
recruiterNav/interviewerNav split) and logout works. Run the backend test
suite. Report per CLAUDE.md's format.
```

---

## Session 2 — Goal 2: Job openings

```
Implement README goal 2 in full: recruiters create job openings (title,
department, description, status open/closed) and edit them later; openings
can be archived and restored; archiving hides from default views without
touching its applications. Recruiter-only for all writes — interviewers can
GET but not create/edit/archive (write a test proving a 403 for
interviewers on each write endpoint).

Backend: JobOpening model already exists in app/models.py — don't redefine
it. Add app/schemas/openings.py, app/services/openings.py (business logic:
archive/restore, default-view filtering), app/routers/openings.py
(CRUD + archive + restore endpoints). Default list view excludes archived
unless a query param asks for them — pick a query param name and use it
consistently, because goal 6's search/filter will need the same
"include archived or not" behavior later and should reuse this pattern
rather than inventing a second one.

Frontend: an openings list page and a create/edit form. Archived openings
are visually distinct (use the existing stage-color/design tokens
convention) and have a restore action.

Write tests covering: create, edit, archive hides from default list but not
from an "include archived" query, restore brings it back, and the
interviewer-403 cases above. Report per CLAUDE.md's format.
```

---

## Session 3 — Goal 3: Applications inside job openings

```
Implement README goal 3: every application belongs to exactly one job
opening and carries candidate_name, candidate_email, source, notes.
Applications can be created and edited (recruiter-only — same 403 pattern
as goal 2; unlike some systems, there's no "any authenticated user can act
until we have assignment data" gap to worry about here — interviewers have
had zero application-level access since goal 1's require_recruiter/
require_interviewer split, and that doesn't change until goal 5 gives them
their first real endpoint). Opening a job opening's detail page shows its
applications.

Backend: Application model already exists — don't redefine it, but this is
also the right time to write the ApplicationHistoryEntry "created" event:
when an application is created, write a CREATED history entry
(old_stage=None, new_stage=APPLIED) in the same service call, since goal 9
requires every application to show when it was created in its timeline.
Add app/schemas/applications.py, app/services/applications.py,
app/routers/applications.py (nested under or filtered by job_opening_id).

Frontend: job opening detail page listing its applications, and a
create/edit application form.

Tests: create, edit, validation (required fields), the CREATED history
entry actually gets written, interviewer-403 on create/edit. Report per
CLAUDE.md's format.
```

---

## Session 4 — Goal 4: Pipeline with rules (highest risk)

```
Implement README goal 4 exactly — this is the core business logic of the
whole app, re-read the goal's full paragraph in README.md before starting.

Before writing any code, output:
1. The full transition table: every (current_stage, action) pair and what
   it produces — either the new stage, or a rejection with the exact
   message text you'll return.
2. Confirmation of what happens to stage_changed_at, rejected_from_stage,
   stall_dismissed_at, and stall_dismissed_stage on each transition type.

Stop and show me that before implementing, so I can check it against the
README first.

The state machine: Applied → Screening → Interview → Offer → Hired, one
stage at a time. Rejected reachable from any active (non-Hired,
non-Rejected) stage, immediately halting progress. A rejected application is
never deleted; it can be reinstated back to the EXACT stage it was rejected
from (stored in rejected_from_stage), not reset to Applied. Any attempt to
skip a stage forward must be rejected by the server with a message
explaining why — write a test for skipping from every stage, not just one
example.

Important: on EVERY transition that changes current_stage (advance, reject,
reinstate — all three, not just advance), update stage_changed_at to now,
AND clear stall_dismissed_at/stall_dismissed_stage back to null. If you skip
the clear step, a dismissal from a previous time the application was in a
given stage can silently suppress a genuinely new stall period after a
reject-then-reinstate cycle back into that same stage — that bug won't show
up until goal 10, but the fix belongs here where the transition logic lives.

Put all of this in app/services/pipeline.py as pure functions/methods that
take the current application state and the requested action and either
perform it or raise a clear domain error (which the router translates to a
4xx with the explanatory message). This service is what goal 7's bulk
actions will call too, so design it to be called for a single application
cleanly. Every transition writes an ApplicationHistoryEntry with correct
old_stage/new_stage/event_type/actor. Recruiter-only.

Frontend: on the application detail page, stage-change controls (advance /
reject / reinstate as applicable to current state) and inline display of
the server's rejection message when a move is invalid.

Tests — be thorough here, this is the highest-value logic in the whole
assignment: valid single-step advance from every stage, illegal skip from
every stage with the right error, reject from every active stage, reinstate
only valid when current_stage==REJECTED and restores rejected_from_stage
exactly, reinstate attempted from a non-rejected state fails,
stage_changed_at updates on every transition type including reinstate,
stall_dismissed fields clear on every transition, interviewer gets 403 on
all of these. Report per CLAUDE.md's format.
```

---

## Session 5 — Goal 5: Interview panel

```
Implement README goal 5: any number of interviewers can be assigned to an
application; an interviewer can be assigned to any number of applications
across every opening; only users with the interviewer role may be assigned
(test that assigning a recruiter-role user is rejected); every interviewer
can see one list of every application they're on the panel for.

This is the first goal that gives interviewers any application-level
access at all — there's no earlier "loosen this route now that assignment
data exists" retrofit needed the way there might be in a system where
multiple roles shared routes from the start. Applications have been
recruiter-only since goal 1.

Backend: ApplicationInterviewer join table already exists. Add
assign/unassign endpoints (recruiter-only) in the applications router or a
new panel router, and a GET endpoint scoped to the current interviewer
(interviewer-only, "my assigned applications" — role-checked via
require_interviewer, filtered by the join table, not by a client-supplied
user id).

Frontend: on the recruiter's application detail page, an interviewer
assign/unassign control (only interviewer-role users selectable). A new
"My Assignments" page for interviewers (the interviewerNav link in
Layout.jsx already points at /my-assignments) listing their panel with a
link into each application's detail/feedback view.

Tests: assignment success, assign-non-interviewer rejected, unassign,
interviewer's list only shows their own applications, interviewer cannot
fetch an application they're not assigned to (403 or 404 — pick one and be
consistent). Report per CLAUDE.md's format.
```

---

## Session 6 — Goal 6: Finding candidates (server-side search/filter/sort/pagination)

```
Implement README goal 6: one list, recruiter-scoped, showing applications
across every opening the recruiter can see. Server-side text search over
candidate_name and candidate_email, filters for job_opening, stage, and
source, sorting by applied date / stage / last update, and pagination
showing the total number of matches. Everything happens in the SQL query —
check your own implementation for accidentally loading everything into
Python and filtering/sorting/paginating there before you commit.

Backend: a single GET endpoint (e.g. GET /applications with query params:
search, job_opening_id, stage, source, sort, page, page_size) in
app/services/applications.py, building the query with SQLAlchemy filters
dynamically. Response includes total count alongside the page of results.
Recruiter-only (goal 5's interviewer list is the separate, already-built
panel-scoped endpoint — don't merge them).

Frontend: an applications list page — search box, filter dropdowns, sort
control, pagination controls — calling the backend with query params on
every change rather than filtering client-side.

Tests: search matches name and email, each filter independently and
combined, each sort order, pagination page/page_size and total count
correctness, interviewer gets 403. Report per CLAUDE.md's format.
```

---

## Session 7 — Goal 7: Bulk operations and CSV export

```
Implement README goal 7, two separate features:

1. Bulk advance / bulk reject: accept a list of application IDs and one
   action. For each application, call the same pipeline service logic from
   goal 4 (don't reimplement the rules) and collect a per-application
   result: {application_id, success: bool, message: str}. One ineligible
   application never fails the whole batch — every application gets its
   own result. Recruiter-only.

2. CSV export: a separate endpoint returning a CSV file of every
   application NOT in a terminal stage (current_stage not in
   {HIRED, REJECTED} — this is the resolved interpretation in CLAUDE.md,
   don't reinterpret it), with at minimum candidate name, email, job
   opening title, current stage, and applied date as columns. Recruiter-only.

Frontend: on the applications list page (goal 6), row selection checkboxes,
a bulk-advance and bulk-reject action showing per-row success/failure after
the call, and a CSV export button/link.

Tests: bulk action with a mixed batch (some eligible, some not — e.g. one
application that would need an illegal skip) returns correct per-item
results and the eligible ones actually moved while ineligible ones didn't;
CSV export excludes Hired/Rejected and includes everything else regardless
of job opening status; interviewer gets 403 on both. Report per CLAUDE.md's
format.
```

---

## Session 8 — Goal 8: Dashboard

```
Implement README goal 8: a recruiter-only landing view with headline
numbers (open positions, active applications [not Hired/Rejected],
interviews scheduled this week, hires this month), a breakdown of
applications by job opening and by stage, and a chart of applications
received per week over the last quarter (~13 weeks). This is recruiter-only
throughout — consistent with goal 1 and the design decision that
interviewers never see cross-opening pipeline data, don't add an
interviewer-scoped variant.

Use the resolved definitions in CLAUDE.md — "interviews scheduled this
week" and "hires this month" are both derived from ApplicationHistoryEntry
(STAGE_CHANGE events with new_stage=INTERVIEW / new_stage=HIRED
respectively, filtered by created_at), not from any new field.

Backend: a single dashboard endpoint aggregating all of this server-side
(SQL aggregation, not fetching everything and counting in Python).

Frontend: replace the placeholder home page from goal 1 with the real
dashboard — headline number cards, a by-opening/by-stage breakdown (table
or grouped display using the existing stage-color tokens), and a Recharts
line or bar chart for applications-per-week. This becomes the "/" route
recruiters land on.

Tests: each KPI's number against known seeded/created data, the by-opening
and by-stage breakdowns, the weekly chart data shape, interviewer gets 403.
Report per CLAUDE.md's format.
```

---

## Session 9 — Goal 9: Immutable history and feedback

```
Implement README goal 9's remaining pieces (the CREATED, STAGE_CHANGE,
REJECTED, REINSTATED events already get written by goals 3/4 — verify
that, don't rewrite it). What's left: feedback, and surfacing the timeline.

1. A feedback endpoint: interviewer-only, and only for applications they're
   actually assigned to (403 otherwise — reuse the goal-5 assignment
   check). Writes a FEEDBACK ApplicationHistoryEntry with feedback_text and
   the interviewer as actor. No edit or delete endpoint for history
   entries — don't add one.
2. A GET endpoint returning an application's full history in chronological
   order (id, event_type, old_stage, new_stage, feedback_text, actor name,
   created_at) — accessible to the recruiter, and to an interviewer only for
   applications they're assigned to.

Frontend: a timeline component on the application detail page showing every
event with who/when, and a feedback form for interviewers on their assigned
applications' detail view.

Tests: feedback write succeeds for assigned interviewer, 403 for
unassigned interviewer, 403 for recruiter (interviewers leave feedback, not
recruiters, per goal 1 — flag it in your report if you read this
differently), history read returns events in order with correct actor
attribution. As a final check, grep the whole codebase for any route that
issues UPDATE or DELETE against ApplicationHistoryEntry and confirm there
is genuinely none. Report per CLAUDE.md's format.
```

---

## Session 10 — Goal 10: Stalled-application alerts (second highest risk)

```
Implement README goal 10 exactly, including the dismiss/reappear lifecycle
— re-read that goal's full paragraph before starting.

Before writing any code, write out the reappearance rule in plain English —
when exactly does a dismissed alert reappear, and when does it correctly
stay dismissed — and check it against CLAUDE.md's resolved decision on
stall_dismissed_at/stall_dismissed_stage before implementing.

An application is "stalled" if it's sat in the same stage for more than ten
days (now - stage_changed_at > 10 days) and current_stage is not HIRED or
REJECTED (terminal stages are never "stalled"). Alerts appear in an alerts
area with a count badge in the navigation. A recruiter can dismiss an alert
for a specific application. If that application later advances and then
stalls again in its new stage for the same length of time, the alert
returns.

The schema already supports this: Application.stall_dismissed_at and
stall_dismissed_stage, and goal 4 should already be clearing both on every
stage transition. The reappearance rule falls out of comparing
stall_dismissed_stage to current_stage — don't add new state to solve it.
If goal 4 did NOT implement the clear-on-transition step, fix it there
first, not with a workaround here.

Implement: a GET alerts endpoint (recruiter-only, returns currently-stalled
applications minus ones with a dismissal matching their current stage), and
a dismiss endpoint (recruiter-only, sets stall_dismissed_at=now,
stall_dismissed_stage=current_stage).

Frontend: an Alerts page (Layout.jsx already has the nav link) listing
stalled applications with a dismiss action, and a live count badge next to
"Alerts" in the sidebar.

Tests — be thorough, this is the trickiest lifecycle in the whole app:
application stalled >10 days appears; <10 days doesn't; dismiss removes it
from the list; dismissed application that then advances stage and re-stalls
in the new stage reappears; dismissed application that stalls again in the
SAME stage (never advanced) does NOT reappear; a rejected-then-reinstated
application that stalls again in the reinstated stage reappears even if it
had a stale dismissal from before the rejection; Hired/Rejected
applications never appear even if old. Write that reject/reinstate case
explicitly — it's the one most likely to be silently wrong. Report per
CLAUDE.md's format.
```

---

## Session 11 — Review pass

```
Do a review pass, not new features.

- Run the full pytest suite and the frontend production build. Fix
  anything failing.
- Re-check every "enforced on the server" and "rejected by the server"
  requirement in README.md against the actual route/service code, not the
  UI — grep for every require_recruiter/require_interviewer usage and
  confirm it lines up with README goal 1's description of what each role
  can and can't do.
- Confirm every role check happens in a dependency or service function, not
  conditional rendering in a frontend component.
- Specific check: confirm stage_changed_at, stall_dismissed_at, and
  stall_dismissed_stage all update/clear correctly on every one of advance,
  reject, and reinstate — not just advance. Trace through a
  dismiss → reject → reinstate → re-stall sequence by hand against the code
  and confirm it produces the reappearing alert goal 10 requires.
- Confirm the CSV export and bulk-action endpoints reuse the goal 4 pipeline
  service and goal 6 query logic rather than duplicating either.
- Flag anything else you're not fully confident about instead of silently
  leaving it.
```

---

## Session 12 — Seed data and deployment config

```
Prepare for deployment.

- A realistic seed script (extend backend/app/seed.py from goal 1): at
  least 2-3 job openings (mix of open/closed, one archived), 20-30
  applications spread realistically across all stages including some
  Rejected and Hired, a few with interviewers assigned and feedback left,
  at least one genuinely stalled (backdate stage_changed_at) and one
  dismissed-then-restalled to prove goal 10 visibly. At least 2 recruiter
  and 2 interviewer demo users with known credentials — print them.
- Run the full backend test suite and `npm run build` for the frontend.
  Fix anything broken.
- Write deployment config for Render (backend) — a render.yaml or
  documented build/start commands — and document the Vercel build settings
  for the frontend and the env vars each needs (DATABASE_URL,
  JWT_SECRET_KEY, CORS_ORIGINS for backend; VITE_API_URL for frontend). Do
  not attempt to actually deploy or create any accounts — I'll do that
  myself. Make sure nothing secret is hardcoded anywhere and .env.example
  files list variable names only.
- Do NOT touch docs/plan.md, docs/schema.md, docs/architecture.md,
  docs/decisions.md, docs/ai-prompts.md, or SUBMISSION.md — those come next
  and some of them I'm writing myself, not you.

Report back with: the seed data summary (what got created, and the demo
credentials), the final test suite + build results, and the deployment
config you wrote.
```

---

## Session 13 — Docs drafts (architecture.md, schema.md, SUBMISSION.md scaffolding only)

```
Draft docs/architecture.md and docs/schema.md, and fill in SUBMISSION.md's
stack table and goal checklist, based on what's actually in this repo right
now — read the real code, don't describe what the README asked for, describe
what got built. Cover architecture.md's four questions (moving pieces and
how they talk to each other, where each runs, the request path for one
representative user action end to end — pick applying a stage change and
trace it from the frontend click through to the DB write and back, and what
you decided not to build). Cover schema.md's five questions (every table's
columns/types, one-to-many vs many-to-many relationships, which constraints
are DB-enforced vs application-enforced and why, what got denormalized, what
would break first at 100x the data).

Do NOT touch docs/decisions.md, docs/plan.md, or docs/ai-prompts.md — I'm
writing those myself, not delegating them to you.
```

---

## Don't delegate these three

Write `docs/decisions.md`, `docs/plan.md`, and `docs/ai-prompts.md`
yourself. They're a record of *your* judgment and process — the brief
explicitly grades whether you can explain your own reasoning three weeks
from now, and "the AI wrote it" is called out as the one answer that fails
this round. The prompts in this playbook, your session reports, and
`CLAUDE.md`'s resolved-decisions list are good raw material for
`ai-prompts.md` and `decisions.md` — but the "what I corrected and why"
needs to come from you actually having read each diff, not from
copy-pasting a report. If you want a second pair of eyes turning that raw
material into a first draft, bring it back to the chat conversation — but
read, edit, and personalize every line before it goes in your submission.
