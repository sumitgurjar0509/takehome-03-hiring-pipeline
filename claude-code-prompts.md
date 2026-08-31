# Claude Code prompts — run in order

Paste these into Claude Code one at a time, in this order, inside this repo
(CLAUDE.md loads automatically as context). Wait for each one to finish, get
its report, hand that report to me (the chat Claude) so I can update
`docs/*.md`, then move to the next prompt. Don't skip ahead.

---

## Prompt 0 — Resume and verify

```
Read CLAUDE.md and README.md in full. Set up the local dev environment
(Postgres role/DBs, backend venv + deps, .env from .env.example, frontend
npm install) per the "How to run things locally" section. Run the existing
backend test suite and confirm all tests still pass. Do not write any new
feature code yet. Report back using the report format at the bottom of
CLAUDE.md, with "Implemented" describing environment status rather than a
feature.
```

---

## Prompt 1 — Goal 1: Accounts and roles (finish it)

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
   somewhere to land (it'll become the real dashboard in goal 8 — don't
   build dashboard content now, just enough to prove the login flow works).

Verify end-to-end manually: run both dev servers, log in as each seeded
role, confirm the sidebar nav differs by role (per Layout.jsx's existing
recruiterNav/interviewerNav split) and logout works. Run the backend test
suite. Report per CLAUDE.md's format.
```

---

## Prompt 2 — Goal 2: Job openings

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
unless a query param asks for them.

Frontend: an openings list page and a create/edit form. Archived openings
are visually distinct (use the existing stage-color/design tokens
convention) and have a restore action.

Write tests covering: create, edit, archive hides from default list but not
from an "include archived" query, restore brings it back, and the
interviewer-403 cases above. Report per CLAUDE.md's format.
```

---

## Prompt 3 — Goal 3: Applications inside job openings

```
Implement README goal 3: every application belongs to exactly one job
opening and carries candidate_name, candidate_email, source, notes.
Applications can be created and edited (recruiter-only — same 403 pattern
as goal 2). Opening a job opening's detail page shows its applications.

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

## Prompt 4 — Goal 4: Pipeline with rules

```
Implement README goal 4 exactly — this is the core business logic of the
whole app, read the goal's full paragraph in README.md again before
starting. The state machine: Applied → Screening → Interview → Offer →
Hired, one stage at a time. Rejected reachable from any active (non-Hired,
non-Rejected) stage, immediately halting progress. A rejected application
is never deleted; it can be reinstated back to the EXACT stage it was
rejected from (stored in rejected_from_stage), not reset to Applied. Any
attempt to skip a stage forward must be rejected by the server with a
message explaining why — write a test for skipping from every stage, not
just one example.

Put all of this in app/services/pipeline.py as pure functions/methods that
take the current application state and the requested action and either
perform it or raise a clear domain error (which the router translates to a
4xx with the explanatory message). This service is what goal 7's bulk
actions will call too, so design it to be called for a single application
cleanly. Every transition (advance, reject, reinstate) writes an
ApplicationHistoryEntry with correct old_stage/new_stage/event_type/actor.
Recruiter-only.

Frontend: on the application detail page, stage-change controls (advance /
reject / reinstate as applicable to current state) and inline display of
the server's rejection message when a move is invalid.

Tests — be thorough here, this is the highest-value logic in the whole
assignment: valid single-step advance from every stage, illegal skip from
every stage with the right error, reject from every active stage, reinstate
only valid when current_stage==REJECTED and restores rejected_from_stage
exactly, reinstate attempted from a non-rejected state fails, interviewer
gets 403 on all of these. Report per CLAUDE.md's format.
```

---

## Prompt 5 — Goal 5: Interview panel

```
Implement README goal 5: any number of interviewers can be assigned to an
application; an interviewer can be assigned to any number of applications
across every opening; only users with the interviewer role may be assigned
(test that assigning a recruiter-role user is rejected); every interviewer
can see one list of every application they're on the panel for.

Backend: ApplicationInterviewer join table already exists. Add
assign/unassign endpoints (recruiter-only) in the applications router or a
new panel router, and a GET endpoint scoped to the current interviewer
(interviewer-only, "my assigned applications" — role-checked via
require_interviewer, filtered by the join table, not by a client-supplied
user id). Confirm/reinforce goal 1's rule here with a test: an interviewer
hitting the general applications endpoints (once they exist) or another
interviewer's applications gets nothing/403 — they only ever see their own
assigned set.

Frontend: on the recruiter's application detail page, an interviewer
assign/unassign control (only interviewer-role users selectable). A new
"My Assignments" page for interviewers (the interviewerNav link in
Layout.jsx already points at /my-assignments) listing their panel with a
link into each application's detail/feedback view.

Tests: assignment success, assign-non-interviewer rejected, unassign,
interviewer's list only shows their own applications, interviewer cannot
see applications they're not assigned to. Report per CLAUDE.md's format.
```

---

## Prompt 6 — Goal 6: Finding candidates (server-side search/filter/sort/pagination)

```
Implement README goal 6: one list, recruiter-scoped, showing applications
across every opening the recruiter can see. Server-side text search over
candidate_name and candidate_email, filters for job_opening, stage, and
source, sorting by applied date / stage / last update, and pagination
showing the total number of matches. Everything happens in the SQL query —
do not fetch everything and filter/sort/paginate in Python or the frontend.

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

## Prompt 7 — Goal 7: Bulk operations and CSV export

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

## Prompt 8 — Goal 8: Dashboard

```
Implement README goal 8: a recruiter-only landing view with headline
numbers (open positions, active applications [not Hired/Rejected],
interviews scheduled this week, hires this month), a breakdown of
applications by job opening and by stage, and a chart of applications
received per week over the last quarter (~13 weeks).

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
and by-stage breakdowns, the weekly chart data shape, interviewer gets 403
(or gets redirected — match whatever ProtectedRoute already does for
role-gated routes on the frontend, but the backend 403 is what matters).
Report per CLAUDE.md's format.
```

---

## Prompt 9 — Goal 9: Immutable history and feedback

```
Implement README goal 9's remaining pieces (the CREATED, STAGE_CHANGE,
REJECTED, REINSTATED events already get written by goals 3/4 — verify
that, don't rewrite it). What's left: feedback, and surfacing the timeline.

1. A feedback endpoint: interviewer-only, and only for applications they're
   actually assigned to (403 otherwise — reuse the goal-5 assignment check).
   Writes a FEEDBACK ApplicationHistoryEntry with feedback_text and the
   interviewer as actor. No edit or delete endpoint for history entries —
   don't add one.
2. A GET endpoint returning an application's full history in chronological
   order (id, event_type, old_stage, new_stage, feedback_text, actor name,
   created_at) — accessible to the recruiter, and to an interviewer only for
   applications they're assigned to.

Frontend: a timeline component on the application detail page showing every
event with who/when, and a feedback form for interviewers on their assigned
applications' detail view.

Tests: feedback write succeeds for assigned interviewer, 403 for
unassigned interviewer, 403 for recruiter (interviewers leave feedback, not
recruiters — confirm this reading of goal 1 is what's built, flag it in
your report if you think it should be different), history read returns
events in order with correct actor attribution, no route anywhere allows
updating or deleting a history entry. Report per CLAUDE.md's format.
```

---

## Prompt 10 — Goal 10: Stalled-application alerts

```
Implement README goal 10 exactly, including the dismiss/reappear lifecycle
— re-read that goal's full paragraph before starting. An application is
"stalled" if it's sat in the same stage for more than ten days
(now - stage_changed_at > 10 days) and current_stage is not HIRED or
REJECTED (resolved in CLAUDE.md — terminal stages are never "stalled").
Alerts appear in an alerts area with a count badge in the navigation. A
recruiter can dismiss an alert for a specific application. If that
application later advances and then stalls again in its new stage for the
same length of time, the alert returns.

The schema already supports this: Application.stall_dismissed_at and
stall_dismissed_stage. The reappearance rule falls out of comparing
stall_dismissed_stage to current_stage — don't add new state to solve it.
Implement: a GET alerts endpoint (recruiter-only, returns currently-stalled
applications minus ones with a dismissal matching their current stage), and
a dismiss endpoint (recruiter-only, sets stall_dismissed_at=now,
stall_dismissed_stage=current_stage).

Frontend: an Alerts page (Layout.jsx already has the nav link) listing
stalled applications with a dismiss action, and a live count badge next to
"Alerts" in the sidebar.

Tests — this is the trickiest lifecycle in the whole app, be thorough:
application stalled >10 days appears; <10 days doesn't; dismiss removes it
from the list; dismissed application that then advances stage and re-stalls
in the new stage reappears; dismissed application that stalls again in the
SAME stage (never advanced) does NOT reappear; Hired/Rejected applications
never appear even if old. Report per CLAUDE.md's format.
```

---

## Prompt 11 — Finish line: seed data, full audit, deploy config, docs

```
All 10 README goals should now be implemented. Do the following, in order,
and don't skip any step:

1. Write/finish a realistic seed script: at least 2-3 job openings (mix of
   open/closed, one archived), 20-30 applications spread realistically
   across all stages including some Rejected and Hired, a few with
   interviewers assigned and feedback left, at least one genuinely stalled
   (backdate stage_changed_at) and one dismissed-then-restalled to prove
   goal 10 visibly. At least 2 recruiter and 2 interviewer demo users.
2. Run the full backend test suite and the frontend production build
   (npm run build). Fix anything broken.
3. Re-read README.md goal by goal and map each one to what's actually
   implemented. Note anything missing, partial, or where you made an
   assumption — don't paper over gaps.
4. Write deployment config for Render (backend) — a render.yaml or
   documented build/start commands — and document the Vercel build settings
   for frontend and the env vars each needs (DATABASE_URL, JWT_SECRET_KEY,
   CORS_ORIGINS for backend; VITE_API_URL for frontend). Do not attempt to
   actually deploy or create any accounts — I'll do that myself. Make sure
   nothing secret is hardcoded anywhere.
5. Do NOT touch docs/plan.md, docs/schema.md, docs/architecture.md,
   docs/decisions.md, docs/ai-prompts.md, or SUBMISSION.md — I'll fill
   those in myself from your reports.

Report back with: the full requirement-by-requirement status (all 10
goals), the final test suite results, the seed data summary, and the
deployment config you wrote.
```
