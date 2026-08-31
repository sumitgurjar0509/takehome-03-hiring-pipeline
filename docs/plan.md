# Plan

## How did you break the work into sessions?

One Claude Code session per README goal (Sessions 1-10), bookended by a
setup/verification session (Session 0), a review pass (Session 11), a
seed-data-and-deploy-config session (Session 12), and a docs-drafting
session (Session 13). Before handing off to Claude Code, an initial
planning phase happened directly with Claude in chat — reading the full
README and docs stubs, resolving stack/scope questions, and scaffolding
the backend's auth, data models, and migrations by hand, which became the
foundation CLAUDE.md and the session prompts were built on.

## What order did you build in, and why that order?

Goal 1 (accounts and roles) first, since every other goal depends on
working auth and RBAC. Goals 2 and 3 (openings, applications) next as
plain CRUD before any business logic. Goal 4 (the pipeline state machine)
came before goals 5-10 deliberately — bulk actions (7), the dashboard's
derived KPIs (8), and stalled alerts (10) all reuse or depend on logic and
data goal 4 establishes (the pipeline service functions, and the
stage_changed_at/stall_dismissed_* reset behavior). Goal 10 was built
last among the ten, since it's the one most dependent on earlier goals'
behavior being correct first.

## What did you estimate versus what it actually took?

Estimated roughly 20-21 hours before starting, based on the README's own
guidance of "about 12 hours ... roughly 2 hours a day across a week" plus
padding for expected AI-collaboration overhead — reviewing session
reports, verifying claims against real evidence rather than trusting them,
and general back-and-forth. Actual total came in under 15 hours, notably
below the padded estimate and closer to the README's own suggested budget.
The session-by-session structure with pre-written, goal-specific prompts
cut down on the back-and-forth clarification that usually eats time. Most
of the unplanned time went into deployment, not development — two real
production bugs (a Python 3.14/SQLAlchemy incompatibility on Render, and
an IPv6 connectivity failure between Render and Supabase's direct
connection) had to be diagnosed from actual error logs and fixed, rather
than being caught by any planning beforehand.

## What did you cut when you ran short?

Nothing — the project came in under its time estimate rather than over,
so no scope was cut. All 10 mandatory README goals were fully implemented,
tested, and verified against real production infrastructure (Session 11's
review pass: 152/152 tests passing; Session 12: realistic seed data;
actual deployment to Render/Vercel/Supabase completed and manually
verified end-to-end). No stretch features were attempted, consistent with
finishing all mandatory goals first.