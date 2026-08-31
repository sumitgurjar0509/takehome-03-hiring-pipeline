## Verifying the environment and confirming understanding of the two highest-risk goals

### Prompt

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

### What you got

Environment confirmed working (7/7 backend tests passing). Accurate restatement of both goal 4 and goal 10, including correctly tracing the reject-then-reinstate-then-re-stall edge case.

### What you corrected

Nothing was factually wrong. Flagged that its "Hired and Rejected are both terminal" framing goes slightly beyond a literal reading of the README (which says reject works "from any stage"), and confirmed that interpretation should be used anyway rather than letting it pass unremarked — logged as Decision 8.

## Building the login flow and seed data (Goal 1 completion)

### Prompt

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

### What you got

Working idempotent seed script, a Login page with inline error handling on failed auth, and App.jsx fully wired with AuthProvider/BrowserRouter/ProtectedRoute. Verified end-to-end via a real headless-browser session — 5 scenarios (logged-out redirect to /login, recruiter login showing correct role-based nav, logout, interviewer login showing only "My Assignments," wrong-password inline error) all passed. 7/7 backend tests still passing.

### What you corrected

Nothing was wrong with the implementation itself. Noted that it installed a scratch Playwright/Chromium setup on its own to do the manual browser verification — not part of the repo or its dependencies, but technically a new tool introduced without asking first, per CLAUDE.md's rule. Flagged as a process note rather than a real problem, since it's local verification tooling only.


## Building job openings CRUD and archive/restore (Goal 2)

### Prompt

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

### What you got

Full CRUD + archive/restore backend (schemas/services/router), 11 new tests (18 total passing), and a frontend list page + shared create/edit form, gated appropriately by role. Verified end-to-end via headless browser across 7 scenarios (create, edit, archive, toggle-show-archived, restore, interviewer read-only view, interviewer blocked from /openings/new).

### What you corrected

The first headless-browser verification run reported false failures on the create/edit steps (list showed 0 rows right after navigating) — caused by checking the DOM before the list page's async fetch had resolved, not an application bug. A screenshot from that same run showed the opening had actually been created correctly, which is what caught the discrepancy. Fixed by adding a wait for the expected element before counting; the rerun passed all 7 scenarios.


## Building applications inside job openings (Goal 3)

### Prompt

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

### What you got

Full CRUD backend (schemas/services/two routers), 11 new tests (29 total passing) covering creation, both validations, the opening-scoping check, the CREATED history entry's correctness, and both interviewer-403 cases. Frontend opening-detail page with an applications table and a shared create/edit form. Verified end-to-end via headless browser across 5 scenarios including interviewer being blocked from both the detail page and the create form on direct navigation.

### What you corrected

Same class of issue as Goal 2: the verification script twice reported false failures from checking the DOM before an async fetch resolved (this time on the opening detail page's empty-applications state). Each time, the screenshot from that same run showed the feature working correctly, confirming it was a test-script race, not an app bug. Fixed with a wait for the expected element before counting.

## Implementing the pipeline state machine with a pre-code checkpoint (Goal 4)

### Prompt

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

### What you got

A complete, correct transition table (forward-only advance with exact rejection messages per illegal target, reject legal from every active stage, reinstate legal only from Rejected) and a side-effects table (stage_changed_at update plus stall_dismissed_* clearing on every successful transition type, regardless of type). After confirmation: a full implementation — pipeline.py service, three new endpoints, a StageBadge component, and 52 new tests (81 total) — including a two-tab race test that verified the real button-click-to-error-message UI wiring, not just the backend logic in isolation.

### What you corrected

The checkpoint itself re-surfaced a question already resolved in Session 0 (whether a Hired application can be rejected) — because that resolution had only been written into a decisions.md draft, never actually added to CLAUDE.md, so it wasn't in this session's context. Confirmed the same answer again, and this time added it directly to CLAUDE.md so it can't get re-asked a third time — a documentation-process fix, not a code fix.

## Building interview panel assignment and interviewer-scoped access (Goal 5)

### Prompt

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

### What you got

Full assignment backend (schemas/service/router), 14 new tests (95 total) covering role validation, idempotent double-assign, cross-opening assignment, both 403 checks, and both branches of the now-role-aware application-detail endpoint. Frontend panel management UI for recruiters and a new read-only detail view plus "My Assignments" page for interviewers. Verified end-to-end via headless browser across 5 scenarios.

### What you corrected

The first verification run reported a false failure and then crashed. Traced it to the test script itself, not the app: two candidate names generated from Date.now() landed in the same millisecond, so "Assigned Candidate 123" ended up a literal substring of "Unassigned Candidate 123," causing a has-text selector to match the wrong row and assign the interviewer to the wrong application in the test. Confirmed via screenshot rather than assuming, then fixed by using genuinely distinct test names.

## Building server-side search, filter, sort, and pagination (Goal 6)

### Prompt

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

### What you got

A single dynamic SQLAlchemy query handling search, three independent filters, six sort options (including pipeline-order stage sorting), and offset/limit pagination with a separate total count. 17 new tests (112 total) covering every filter/sort combination, pagination correctness, interviewer 403, and input validation. Frontend list page with debounced search and live filter/sort/pagination controls.

### What you corrected

The pipeline-order stage sort failed on first run against real Postgres (psycopg2 DataError: invalid input value for enum). The dict-based SQLAlchemy `case({...}, value=col)` form doesn't propagate the column's ENUM type to its bound parameters. Fixed by rewriting it as explicit per-condition tuples, which ties each literal to the column comparison correctly — caught by an actual test failure against the real database, not guessed around.

## Building bulk actions and CSV export (Goal 7)

### Prompt

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

### What you got

Bulk advance/reject built directly on top of goal 4's advance()/reject() functions with no rule duplication, returning a per-application {id, success, message} result. CSV export matching the resolved "not in a terminal stage" definition, verified independent of job opening status. 13 new tests (125 total), including mixed-batch tests that check both the application row and the history table for phantom entries on failed items.

### What you corrected

It claimed the correct route registration order (static paths like /export and /bulk registered before the dynamic /{application_id} segment) was "based on the goal-5 lesson about Starlette's route matching" — implying a real incident had happened in an earlier session. Checked goal 5's actual report and commit: no such incident occurred. Goal 5's only reported issue was an unrelated Playwright test-script bug, and its routes never even collided in a way that would have taught this lesson (/my-assignments was a separate top-level path by design; /applications/{id}/interviewers has an extra path segment, so no ambiguity). Confronted directly, it corrected the record: the routing choice itself was correct (general FastAPI/Starlette knowledge — literal paths must be registered before {param} segments when they'd otherwise collide), but the "lesson learned from goal 5" framing was fabricated. The technical decision was never wrong; the story attached to it was.

## Building the dashboard (Goal 8)

### Prompt

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

### What you got

A single dashboard endpoint aggregating all seven pieces server-side via SQL, 8 new tests (133 total) covering each KPI's edge cases, and a frontend Dashboard.jsx with KPI cards, breakdown tables, and a Recharts chart. It also proactively flagged a genuine ambiguity (whether open_positions should exclude archived openings) rather than silently picking a default.

### What you corrected

The Recharts bar initially rendered invisible: `fill="var(--color-brand)"` reached the DOM as a literal unresolved string because Recharts sets fill as a raw SVG attribute rather than an inline style, and CSS custom-property resolution there is inconsistent across browsers. Diagnosed via a direct DOM inspection showing the unresolved string (not guessed at), fixed with a small hook that resolves the token via getComputedStyle before handing Recharts a literal color, and verified fixed via a second DOM inspection plus a screenshot. Separately confirmed a full-page-screenshot rendering glitch during verification was a Playwright viewport-resize artifact, not a real bug, by comparing against a normal-viewport screenshot.

Also: correctly flagged (rather than silently resolved) whether open_positions should exclude archived-but-open job openings — a genuine ambiguity CLAUDE.md hadn't covered. After confirming "exclude archived," fixed the query and extended the existing KPI test to cover it; full suite (133) still passing.

## Building feedback and the immutable history timeline (Goal 9)

### Prompt

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

### What you got

Feedback and history endpoints reusing goal 5's assignment-check logic (extracted into a shared internal helper rather than duplicated), 9 new tests (142 total) including a full create→advance→feedback→reject→reinstate sequence verified via a single GET history call, and a grep-confirmed absence of any UPDATE/DELETE against the history table. Frontend Timeline component shared between the recruiter's edit view and the interviewer's feedback view.

### What you corrected

Nothing broke this session. It did proactively flag and defend a real design asymmetry (404 on reads vs 403 on the feedback write for the same "not your application" condition) rather than silently leaving it unexplained or "fixing" it into false consistency — confirmed as intentional, logged as Decision 26.


## Building stalled-application alerts and the dismiss/reappear lifecycle (Goal 10)

### Prompt

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

### What you got

A single query-time comparison (stall_dismissed_stage vs current_stage) with no new state, exactly matching the resolved design — since goal 4 already clears both dismissal columns on every transition. 10 new tests (152 total), including the explicit reject→reinstate→re-stall case verified via direct field assertions rather than just observed behavior. A live sidebar badge count and full Alerts page.

### What you corrected

Caught during its own end-to-end verification, not by a failing test: the sidebar badge only refetched on mount and after an explicit dismiss, which goes stale between page navigations since stalling is purely time-driven and isn't triggered by any in-app action the badge could hook into. Fixed by also refetching on every route change. This is a real product bug, not test flakiness — a badge that only updates on specific actions doesn't actually track a value that changes with the passage of time alone.

A separate, smaller lesson from the same session: a boundary test using stage_changed_at set to exactly 10 days ago failed on first run — not an app bug, but because real wall-clock time elapses between the fixture setup and the query running, making "exactly 10 days" at setup time into "just over 10 days" by query time. Fixed by testing a value with a small safety margin under the threshold instead of an unreachable exact instant.

## Review pass before deployment (Session 11)

### Prompt

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

### What you got

152/152 tests and a clean frontend build, confirmed. Every route's auth dependency checked systematically (a script, not just grep). Full permission matrix re-verified against README goal 1's wording, including confirming JobOpeningOut's fields can't leak pipeline data through the both-roles-open openings endpoints. Stall-dismissal fields traced field-by-field through a real reject/reinstate cycle, matching the automated test's result independently. Confirmed bulk actions fully reuse goal 4's pipeline functions; confirmed CSV export deliberately does NOT reuse goal 6's search function (with reasoning for why), while both correctly share the single TERMINAL_STAGES source of truth.

### What you corrected

Nothing needed fixing — this was a clean pass. It proactively named the one case worth double-checking (Dashboard's component-level role redirect) rather than letting a technically-true "role check happens in conditional rendering" go unaddressed just because the underlying data access is independently server-enforced.


## Seed data and deployment configuration (Session 12)

### Prompt

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

### What you got

Seed data built entirely through real pipeline function calls rather than fabricated rows, including a dedicated stalled candidate and a dedicated dismiss-then-reappear candidate, both independently verified via direct DB query and a live API call. render.yaml with migrations run via preDeployCommand, env vars correctly split between manual/secret and auto-generated, and a new docs/deploy.md with full setup instructions. Confirmed no secrets hardcoded and no excluded docs files touched.

### What you corrected

Nothing was wrong in what it built, but flagged two things for verification before actual deployment: its claim about Render's preDeployCommand being available on the free plan is an unverifiable third-party platform detail that should be double-checked against the live dashboard rather than trusted outright; and confirmed docs/deploy.md needs to explicitly cover the CORS_ORIGINS/VITE_API_URL circular dependency (Render needs Vercel's URL, Vercel needs Render's URL, so the backend's CORS setting has to be revisited after the frontend deploys).