## Decision 1

- **Chose:** Sync SQLAlchemy (not async)
- **Rejected:** Async SQLAlchemy with async FastAPI routes
- **Why:** Simpler to reason about and explain in an interview. FastAPI runs sync routes in a threadpool, which is sufficient at this app's scale.

## Decision 2

- **Chose:** bcrypt + PyJWT, used directly
- **Rejected:** passlib (for hashing), python-jose (for JWT)
- **Why:** passlib has known compatibility friction with bcrypt >=4.1. python-jose is less actively maintained. Fewer moving parts, more current libraries.

## Decision 3

- **Chose:** Manual regex email validation
- **Rejected:** Pydantic's built-in `EmailStr`
- **Why:** `EmailStr` requires the `email-validator` package, which wasn't in the approved dependency list. Avoided adding a dependency just for this.

## Decision 4

- **Chose:** Job opening `status` (open/closed) and `archived` (boolean) as two separate fields
- **Rejected:** A single combined status field (e.g. status includes an "archived" value)
- **Why:** The README describes them as conceptually distinct — status reflects whether the position is actively hiring, archived controls default-view visibility without deleting its applications.

## Decision 5

- **Chose:** Stalled-alert dismissal state stored as two columns directly on `Application` (`stall_dismissed_at`, `stall_dismissed_stage`)
- **Rejected:** A separate dismissal-history table
- **Why:** Simpler, and the reappearance rule falls out of directly comparing stage values.
- **Later reversed:** Not the column design itself, but the transition rule around it — while writing the goal 4 transition logic, realized a reject-then-reinstate cycle back into a previously-dismissed stage could leave a stale dismissal that incorrectly matches the stage again. Fixed by clearing both columns on every transition (advance, reject, reinstate).

## Decision 6

- **Chose:** CSV export's "every open application" interpreted as "not in a terminal stage" (`current_stage` not in `{HIRED, REJECTED}`)
- **Rejected:** Interpreting "open" as "belongs to a job opening with status=open"
- **Why:** Reads more naturally as describing the application's own state rather than its parent opening's status.

## Decision 7

- **Chose:** "Interviews scheduled this week" dashboard KPI derived from `ApplicationHistoryEntry` (stage-change events into `INTERVIEW`, filtered by date)
- **Rejected:** Adding a new interview-date/time field to the application
- **Why:** The README explicitly closes the list of application fields in goal 3. Adding a new field would go beyond spec without approval.

## Decision 8

- **Chose:** `Hired` and `Rejected` both treated as terminal — a Hired application cannot be rejected
- **Rejected:** A literal reading of goal 4's "reject from any stage" that would include Hired
- **Why:** Matches the existing schema's `TERMINAL_STAGES` set and makes domain sense — rejecting a hire is HR/termination territory, outside this pipeline's scope.

## Decision 9

- **Chose:** Archive/restore implemented as separate POST action endpoints (POST /openings/{id}/archive, POST /openings/{id}/restore) rather than folded into the general PATCH /openings/{id} update endpoint
- **Rejected:** Handling archive/restore as a field update via PATCH (e.g. PATCH with {"archived": true})
- **Why:** Keeps the recruiter-only write surface easy to test discretely (one 403 test per action), and matches the explicit verb-like nature of archiving as an action distinct from editing opening details — consistent with the earlier decision that archived is orthogonal to status.

## Decision 10

- **Chose:** All application endpoints (including GET/list) are recruiter-only — interviewers get zero application-level access at this point
- **Rejected:** Symmetric access like goal 2's openings, where GET is open to both roles
- **Why:** Letting interviewers list/view all applications now would be a real, if temporary, over-exposure — goal 5's assignment-based filtering is what's supposed to scope down what an interviewer can see, and that doesn't exist yet.

## Decision 11

- **Chose:** Split the applications router into a nested path (POST create / GET list, scoped under an opening) and a flat path (GET / PATCH by the application's own id)
- **Rejected:** Nesting every application route under its opening
- **Why:** An edit form for an existing application doesn't need to know or care which opening it belongs to, and goals 4, 5, and 9 will all reference applications by their own id, not by opening.


## Decision 12

- **Chose:** The advance endpoint requires the client to send an explicit `to_stage`, rather than a bodyless "just move to the next stage" endpoint
- **Rejected:** An implicit advance-to-next-stage endpoint with no target parameter
- **Why:** Makes "skip a stage forward" a real, testable illegal-request shape (client explicitly asks for an invalid target) rather than something structurally impossible to even attempt — matches the README's framing of the rule as something the server must actively reject.

## Decision 13

- **Chose:** `pipeline.py`'s functions take an ORM `Application`, mutate it in place, and return an unsaved history entry — they never call `db.add()` or `db.commit()` themselves
- **Rejected:** Having the pipeline functions own the database session and commit their own changes
- **Why:** Keeps the module free of hidden transaction control, and makes it directly reusable by goal 7's bulk-action loop (which needs to process many applications and report per-item success/failure) without rewriting the core logic.

## Decision 14

- **Chose:** HTTP 409 Conflict for illegal pipeline transitions
- **Rejected:** HTTP 422 Unprocessable Entity (same status already used for input validation errors)
- **Why:** A skip-stage request is well-formed input — it just conflicts with the application's current state. That's a different failure mode than malformed input, and deserves a different status code.

## Decision 15

- **Chose:** 404 (not 403) when an interviewer requests an application they're not on the panel for
- **Rejected:** 403 Forbidden, which would confirm the application exists but is off-limits
- **Why:** A 404 avoids leaking the existence of an application to someone who has no visibility into it at all — a stronger default for a resource an interviewer may have zero legitimate reason to know about.

## Decision 16

- **Chose:** A new, separate read-only ApplicationDetail.jsx page for interviewers, instead of reusing the recruiter's ApplicationForm.jsx in a read-only mode
- **Rejected:** One shared component with role-based conditional rendering of edit controls
- **Why:** Every action on the recruiter's form (field edits, pipeline buttons, panel management) is already recruiter-only server-side; reusing it for interviewers would mean either dead/hidden controls or extra role-branching inside an already-large component, for a view that's supposed to be simple.

## Decision 17

- **Chose:** "Stage" sort orders by pipeline position (Applied → Screening → Interview → Offer → Hired, Rejected last)
- **Rejected:** Alphabetical ordering of the stage enum values
- **Why:** Alphabetical order (applied, hired, interview, offer, rejected, screening) would be actively unhelpful for a recruiter scanning where candidates actually stand in the pipeline.

## Decision 18

- **Chose:** Source filter is case-insensitive exact match
- **Rejected:** Partial/substring match, like the name/email search
- **Why:** Source is a small, real-world-constrained field. A partial match risks false positives — e.g. a hypothetical "non-referral" value matching a filter for "referral."

## Decision 19

- **Chose:** Pagination via simple offset/limit
- **Rejected:** Keyset/cursor-based pagination
- **Why:** Appropriate at this app's scale, consistent with the rest of the codebase's straightforward SQLAlchemy usage, and keeps the frontend's Previous/Next UI simple. This is also the concrete answer to docs/schema.md's "what would break first at 100x the data" question — offset pagination degrades on large tables, keyset would be the fix.

## Decision 20

- **Chose:** One endpoint, POST /applications/bulk, with an `action` field selecting advance or reject
- **Rejected:** Two separate endpoints (/bulk-advance, /bulk-reject)
- **Why:** Matches the goal's literal framing ("accept a list of application IDs and one action"), and keeps the per-item result shape identical regardless of which action ran.

## Decision 21

- **Chose:** bulk_advance computes each application's own next stage internally — there's no client-supplied target stage
- **Rejected:** A shared target stage for the whole batch
- **Why:** A batch can span applications at different stages, so "advance" can only sensibly mean "each one moves to its own next stage" — a single shared target wouldn't work for a mixed-stage selection.

## Decision 22

- **Chose:** CSV export built fully in memory via csv.writer/io.StringIO
- **Rejected:** A StreamingResponse that generates rows incrementally
- **Why:** Appropriate at this app's scale and consistent with its overall simplicity. Logged as another concrete answer to docs/schema.md's "what breaks first at 100x the data" question, alongside the offset-pagination decision from goal 6.

## Decision 23

- **Chose:** open_positions KPI counts only openings that are both status=OPEN and not archived
- **Rejected:** Counting status=OPEN regardless of archived status (the initial implementation)
- **Why:** Archiving means "hidden from default views" — a dashboard headline KPI is a default view, so counting an archived opening there would be inconsistent with what archiving is supposed to do everywhere else in the app.
- **Later reversed:** Not reversed exactly, but caught and fixed within the same session — Claude Code's first implementation counted status=OPEN alone and flagged the archived-interaction as an open question rather than silently deciding either way; confirmed the exclusion, and it fixed the query and extended the existing test to assert an archived-but-open opening is excluded.

## Decision 24

- **Chose:** by_opening and by_stage dashboard breakdowns cover every application across all stages, including Hired and Rejected — not just the non-terminal set the "active applications" KPI uses
- **Rejected:** Scoping both breakdowns to active applications only, matching the headline KPI
- **Why:** The headline "active applications" number is deliberately narrow, but the breakdowns read as a general funnel view — showing the full picture including completed hires/rejections is more useful to a recruiter than a truncated one.

## Decision 25

- **Chose:** Dashboard.jsx itself detects a non-recruiter and redirects to /my-assignments, rather than gating the "/" route with ProtectedRoute's roles prop
- **Rejected:** Role-gating "/" directly at the route level
- **Why:** Login.jsx sends every role to "/" post-login; gating "/" by role would bounce an interviewer straight back to "/", creating an infinite redirect loop. Keeping the route itself role-agnostic and handling the redirect inside the component avoids that.

## Decision 26

- **Chose:** GET endpoints (application detail, history) return 404 for an interviewer accessing an application they're not assigned to, while POST /feedback returns 403 for the same underlying condition
- **Rejected:** A single uniform status code across all endpoints for "interviewer, not assigned"
- **Why:** Neither endpoint leaks existence on its own — GET's 404 hides existence entirely (appropriate for a browse/discovery-style read), while feedback's 403 is returned identically whether the application exists or not, so it doesn't distinguish "not found" from "not yours" either. The write path uses 403 because reaching /feedback implies the interviewer already believes they're assigned (they got there through their own UI), so a clear "you're not assigned to this" is more useful there than a generic not-found.

## Decision 27

- **Chose:** GET /alerts returns the full currently-stalled list directly; the sidebar badge count is just that list's length, with no separate count-only endpoint
- **Rejected:** A dedicated lightweight /alerts/count endpoint
- **Why:** At this app's scale the stalled list is small — a second endpoint just to avoid sending a few extra rows isn't worth maintaining separately.

## Decision 28

- **Chose:** The dismiss endpoint doesn't require the application to currently be in a stalled state to accept the dismissal
- **Rejected:** Guarding dismiss so it only succeeds if the application is actually stalled right now
- **Why:** Consistent with how the rest of the app doesn't second-guess valid state changes — in practice the UI only ever shows a Dismiss button next to entries already displayed as stalled, so the guard would be defensive code against a path the UI never creates.

## Decision 29

- **Chose:** The seed script drives every application through the real pipeline.advance()/reject()/dismiss-alert functions, rather than directly setting current_stage and history rows in the database
- **Rejected:** Directly inserting rows with hand-set field values to represent each application's "final" state
- **Why:** Guarantees the seeded history timeline is exactly what the running app itself would produce for that sequence of actions — genuinely realistic demo data, not a fabricated approximation that happens to look right.

## Decision 30

- **Chose:** Database migrations run via Render's preDeployCommand, once per deploy
- **Rejected:** Running alembic upgrade head inside the app's own startup sequence, on every process boot
- **Why:** Avoids re-running migrations on every restart or scale event — migrations should happen once per actual deploy, not every time the process starts.