# Schema

Five tables, one migration (`backend/alembic/versions/00efbc95d414_...py`),
all Postgres native enum types rather than plain strings or a lookup table.

## Table by table

### `users`

| Column | Type | Notes |
|---|---|---|
| `id` | integer, PK | |
| `email` | varchar(255), NOT NULL | unique index |
| `password_hash` | varchar(255), NOT NULL | bcrypt hash, never the plaintext |
| `name` | varchar(255), NOT NULL | |
| `role` | enum `user_role` (`RECRUITER`, `INTERVIEWER`), NOT NULL | |
| `created_at` | timestamptz, NOT NULL | app-side default (`utcnow()`) |

### `job_openings`

| Column | Type | Notes |
|---|---|---|
| `id` | integer, PK | |
| `title` | varchar(255), NOT NULL | |
| `department` | varchar(255), NOT NULL | |
| `description` | text, NOT NULL | app default `""` |
| `status` | enum `opening_status` (`OPEN`, `CLOSED`), NOT NULL | default `OPEN` |
| `archived` | boolean, NOT NULL | default `False`, indexed |
| `created_by_id` | integer, FK -> `users.id`, NOT NULL | |
| `created_at` / `updated_at` | timestamptz, NOT NULL | `updated_at` has a DB-side `onupdate` trigger |

### `applications`

| Column | Type | Notes |
|---|---|---|
| `id` | integer, PK | |
| `job_opening_id` | integer, FK -> `job_openings.id`, NOT NULL | indexed |
| `candidate_name` | varchar(255), NOT NULL | indexed |
| `candidate_email` | varchar(255), NOT NULL | indexed, **not unique** — see below |
| `source` | varchar(255), NOT NULL | app default `""` |
| `notes` | text, NOT NULL | app default `""` |
| `current_stage` | enum `application_stage` (`APPLIED`, `SCREENING`, `INTERVIEW`, `OFFER`, `HIRED`, `REJECTED`), NOT NULL | default `APPLIED`, indexed |
| `rejected_from_stage` | enum `application_stage`, nullable | set only while `current_stage == REJECTED` |
| `stage_changed_at` | timestamptz, NOT NULL | indexed — the stalled-alert query filters on this |
| `stall_dismissed_at` | timestamptz, nullable | |
| `stall_dismissed_stage` | enum `application_stage`, nullable | always set/cleared together with `stall_dismissed_at` |
| `created_by_id` | integer, FK -> `users.id`, NOT NULL | |
| `created_at` / `updated_at` | timestamptz, NOT NULL | |

Composite index `(job_opening_id, current_stage)` in addition to the two
single-column indexes — supports "applications in opening X currently at
stage Y" (goal 3's per-opening view, filtered) without Postgres having to
bitmap-combine two separate indexes on every request.

`candidate_email` is deliberately *not* unique: the same person can apply
to more than one opening, and a rejected candidate can re-apply later
(README goal 4 explicitly keeps rejected applications around rather than
deleting them, so a second application from the same email is a normal,
expected case, not a duplicate to prevent).

### `application_interviewers` (join table)

| Column | Type | Notes |
|---|---|---|
| `application_id` | integer, FK -> `applications.id` | part of composite PK |
| `interviewer_id` | integer, FK -> `users.id` | part of composite PK, also individually indexed |
| `assigned_at` | timestamptz, NOT NULL | |

No surrogate `id` — the composite primary key *is* the uniqueness
guarantee ("this interviewer is on this application's panel, once").

### `application_history_entries`

| Column | Type | Notes |
|---|---|---|
| `id` | integer, PK | |
| `application_id` | integer, FK -> `applications.id`, NOT NULL | indexed |
| `event_type` | enum `history_event_type` (`CREATED`, `STAGE_CHANGE`, `REJECTED`, `REINSTATED`, `FEEDBACK`), NOT NULL | |
| `old_stage` / `new_stage` | enum `application_stage`, nullable | both null for a `FEEDBACK` entry |
| `feedback_text` | text, nullable | only set for a `FEEDBACK` entry |
| `actor_id` | integer, FK -> `users.id`, NOT NULL | |
| `created_at` | timestamptz, NOT NULL | indexed |

Composite index `(application_id, created_at)` — the goal 9 timeline query
is always "every entry for one application, oldest first," and this index
serves that directly instead of an index-then-sort.

## Which relationships are one-to-many, and which are many-to-many?

Every relationship in this schema is one-to-many **except one**:

- `users` -> `job_openings` (creator): one-to-many.
- `users` -> `applications` (creator): one-to-many.
- `users` -> `application_history_entries` (actor): one-to-many.
- `job_openings` -> `applications`: one-to-many — every application
  belongs to exactly one opening (`job_opening_id` is `NOT NULL`, and
  nothing in the app ever reassigns an application to a different
  opening).
- `applications` -> `application_history_entries`: one-to-many.
- **`applications` <-> `users` (interviewers), through
  `application_interviewers`: many-to-many.** This is the only
  many-to-many relationship in the schema, and it's exactly why it's the
  only table here with a join table instead of a plain foreign key: any
  number of interviewers can sit on one application's panel, and any one
  interviewer can sit on any number of applications' panels, across every
  opening (README goal 5).

## Which constraints are enforced by the database, and which by application code — and why?

**Database-enforced:**
- `NOT NULL` on every column the domain always requires.
- Foreign keys everywhere a row references another table — you cannot
  insert an application pointing at a `job_opening_id` that doesn't exist,
  or a history entry pointing at a nonexistent actor. This is exactly the
  kind of invariant that must hold regardless of which code path writes
  the row, so it belongs at the database layer, not re-checked in every
  service function.
- The unique index on `users.email` — two accounts can never share an
  email, full stop, independent of whatever a given request happened to
  validate.
- The composite primary key on `application_interviewers` — "this
  interviewer is on this panel" can only ever be true once per pair. The
  service layer also checks for an existing row before inserting (to stay
  idempotent and return a clean result rather than catching an
  `IntegrityError`), but the actual backstop guaranteeing no duplicate row
  is the primary key, not that check.
- Postgres native enum types for `role`, `status`, `current_stage`,
  `rejected_from_stage`, `stall_dismissed_stage`, `old_stage`/`new_stage`,
  and `event_type` — an invalid value can never be written to these
  columns no matter what application code does or forgets to validate.

**Application-enforced:**
- Every rule that's about *sequence* or *permission* rather than a single
  row's shape: "advance moves exactly one stage forward"; "a hired
  application can never be rejected"; "only interviewer-role users can be
  assigned to a panel" (`services/panel.py`) — this specifically couldn't
  become a database `CHECK` constraint without a trigger that looks up
  another table's column, and this project deliberately doesn't use
  triggers anywhere (see below); role-based authorization
  (`require_recruiter`/`require_interviewer`) — this is a per-request
  access-control decision, not a fact about stored data, so it has no
  natural expression as a table constraint at all.
- Input shape validation — blank-string rejection on names/titles, the
  candidate-email regex format check — lives in Pydantic request schemas,
  not as Postgres `CHECK` constraints. The point of validating here is to
  reject bad input *before* it reaches a query; a `CHECK (trim(name) <>
  '')` constraint would just duplicate that logic in SQL for no benefit,
  since nothing ever writes to these tables except through the
  application's own validated request models.
- `application_history_entries` being append-only (goal 9 — no `UPDATE`
  or `DELETE` ever issued against it) is enforced by **convention**, not a
  database trigger or a `REVOKE UPDATE, DELETE` grant. This is a
  deliberate, already-documented trade-off in the codebase: a trigger
  would make the guarantee airtight against a future bug, but it also
  adds a piece of logic that lives outside the application and is harder
  to reason about or explain later, for a rule this project's own review
  pass already confirmed by grepping the whole codebase for `db.delete()`
  and `.update()` calls. Worth being honest that this is a real gap — a
  future migration or a raw `psql` session could still mutate history
  rows — accepted deliberately in favor of simplicity at this scale.

## What did you deliberately denormalise?

- **`applications.current_stage` and `stage_changed_at` are themselves a
  denormalization.** The "current" state of an application is always
  technically re-derivable — take the most recent
  `STAGE_CHANGE`/`REJECTED`/`REINSTATED` row from
  `application_history_entries` for that application — but the app stores
  it redundantly as live columns on `applications` instead of computing it
  per request. This is *why* goal 4's transition logic has to remember to
  clear `stall_dismissed_at`/`stall_dismissed_stage` on every single
  transition: it's maintaining a denormalized cache of "where is this
  application right now" that every write path has to keep in sync by
  hand. The payoff is that every list, filter, sort, dashboard breakdown,
  and stalled-alert query (goals 6, 8, 10) is one indexed `WHERE`/`ORDER
  BY` against `applications` directly, instead of a correlated subquery
  or window function against the full history table on every page load.
- **`stall_dismissed_at`/`stall_dismissed_stage`** are a small denormalized
  cache of "the most recent dismissal act, for this specific stage,"
  rather than a fully normalized `stall_dismissals` table (one row per
  dismissal event, keyed to the application and the stage it happened in)
  — a real alternative that was considered and explicitly rejected (see
  `docs/decisions.md`). The two columns on `applications` trade away
  dismissal *history* (there's no record that an application was
  dismissed three times across three separate past stalls — each new
  dismissal simply overwrites the last) for a reappearance-rule query
  that's a single equality check against two columns already on the row
  being scanned, instead of a join plus a "most recent dismissal for this
  stage" subquery per application.

`job_opening_id` living directly on `applications` is not counted as
denormalization above — that's just the normal shape of a one-to-many
foreign key, not a redundant copy of derivable data.

## What would break first at 100x the data?

At the current seed scale (~25–40 applications), 100x is roughly 2,500–
4,000 applications — genuinely still small for Postgres, so nothing
breaks on raw row count alone. The honest answer is about *query
patterns* that don't scale linearly with row count, not a hard wall:

1. **Goal 6's search** — `candidate_name.ilike('%term%')` /
   `candidate_email.ilike('%term%')`. A leading-wildcard `ILIKE` can't use
   the existing btree indexes on those columns at all (btree only helps
   with left-anchored patterns), so at 100x this becomes a full table scan
   on every debounced keystroke. This is the first thing that would show
   up as real, user-visible latency — the fix is a `pg_trgm` trigram index
   (or moving search to Postgres full-text search, or an external search
   index), not built here because it needs a dependency outside the
   approved list and isn't needed at today's scale.
2. **The CSV export** (`list_applications_for_export`) loads every
   matching row into Python and builds the entire CSV string in memory
   before responding — fine into the low thousands of rows, but the first
   thing to revisit well before "100x" becomes a real number: streaming
   the response instead of buffering it whole, or moving export to a
   background job for very large exports.
3. **`application_history_entries` grows strictly faster than
   `applications`.** Every creation, stage change, and piece of feedback
   adds a row — an actively-managed pipeline easily produces 5–10 history
   rows per application — so at 100x applications, history is more like
   500–1000x today's row count. The timeline query itself stays fast
   (indexed on `application_id`), but this table has no natural cap since
   nothing ever prunes it (append-only, goal 9). It's the one table with
   genuinely unbounded growth, and would be the first candidate for
   partitioning or archiving old entries in a system that ran for years.
4. **Dashboard `by_opening`/`by_stage` `GROUP BY` queries and the
   stalled-alerts filter** stay full-table aggregates by design (they're
   answering "all of them," deliberately), but they're already indexed on
   the columns they filter/group by (`current_stage`, `stage_changed_at`)
   — these hold up fine well past 100x and aren't the first thing to
   worry about.
