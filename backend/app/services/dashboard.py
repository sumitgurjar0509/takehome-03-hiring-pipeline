"""
Server-side aggregation for the recruiter dashboard (README goal 8). Every
number here comes from a SQL COUNT/GROUP BY — nothing is loaded row by row
into Python and counted there. "Interviews scheduled this week" and "hires
this month" are both derived from ApplicationHistoryEntry (STAGE_CHANGE
events with new_stage=INTERVIEW / new_stage=HIRED respectively, filtered
by created_at) per CLAUDE.md's resolved decision — there is no scheduling
field anywhere in the spec, and REINSTATED events into either stage
deliberately don't count, matching that decision's exact wording.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    TERMINAL_STAGES,
    Application,
    ApplicationHistoryEntry,
    HistoryEventType,
    JobOpening,
    OpeningStatus,
    Stage,
)


def _week_start(reference: datetime) -> datetime:
    """Monday 00:00 UTC of the week containing `reference` (ISO week, matching Postgres date_trunc('week', ...))."""
    start = reference - timedelta(days=reference.weekday())
    return start.replace(hour=0, minute=0, second=0, microsecond=0)


def _month_start(reference: datetime) -> datetime:
    return reference.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _next_month_start(month_start: datetime) -> datetime:
    return (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)


def get_dashboard(db: Session) -> dict:
    now = datetime.now(timezone.utc)

    # Archived means "hidden from default views" (see docs/decisions.md),
    # and a dashboard KPI is a default view — so an archived-but-open
    # opening doesn't count here, even though its status is still OPEN.
    open_positions = (
        db.query(func.count(JobOpening.id))
        .filter(JobOpening.status == OpeningStatus.OPEN, JobOpening.archived.is_(False))
        .scalar()
    )

    active_applications = (
        db.query(func.count(Application.id))
        .filter(Application.current_stage.notin_(TERMINAL_STAGES))
        .scalar()
    )

    week_start = _week_start(now)
    week_end = week_start + timedelta(days=7)
    interviews_scheduled_this_week = (
        db.query(func.count(ApplicationHistoryEntry.id))
        .filter(
            ApplicationHistoryEntry.event_type == HistoryEventType.STAGE_CHANGE,
            ApplicationHistoryEntry.new_stage == Stage.INTERVIEW,
            ApplicationHistoryEntry.created_at >= week_start,
            ApplicationHistoryEntry.created_at < week_end,
        )
        .scalar()
    )

    month_start = _month_start(now)
    next_month_start = _next_month_start(month_start)
    hires_this_month = (
        db.query(func.count(ApplicationHistoryEntry.id))
        .filter(
            ApplicationHistoryEntry.event_type == HistoryEventType.STAGE_CHANGE,
            ApplicationHistoryEntry.new_stage == Stage.HIRED,
            ApplicationHistoryEntry.created_at >= month_start,
            ApplicationHistoryEntry.created_at < next_month_start,
        )
        .scalar()
    )

    by_opening_rows = (
        db.query(JobOpening.id, JobOpening.title, func.count(Application.id))
        .join(Application, Application.job_opening_id == JobOpening.id)
        .group_by(JobOpening.id, JobOpening.title)
        .order_by(func.count(Application.id).desc())
        .all()
    )
    by_opening = [
        {"job_opening_id": row[0], "job_opening_title": row[1], "count": row[2]}
        for row in by_opening_rows
    ]

    by_stage_counts = dict(
        db.query(Application.current_stage, func.count(Application.id))
        .group_by(Application.current_stage)
        .all()
    )
    by_stage = [{"stage": stage, "count": by_stage_counts.get(stage, 0)} for stage in Stage]

    # AT TIME ZONE 'UTC' before truncating: date_trunc on a timestamptz uses
    # the session's timezone setting, which isn't guaranteed to be UTC. This
    # keeps week boundaries deterministic and aligned with _week_start's
    # Python-side UTC computation regardless of server config.
    thirteen_weeks_start = week_start - timedelta(weeks=12)
    week_bucket = func.date_trunc("week", func.timezone("UTC", Application.created_at))
    weekly_rows = (
        db.query(week_bucket, func.count(Application.id))
        .filter(Application.created_at >= thirteen_weeks_start)
        .group_by(week_bucket)
        .all()
    )
    weekly_counts_by_date = {bucket.date(): count for bucket, count in weekly_rows}
    applications_per_week = []
    for i in range(13):
        bucket_date = (thirteen_weeks_start + timedelta(weeks=i)).date()
        applications_per_week.append(
            {"week_start": bucket_date, "count": weekly_counts_by_date.get(bucket_date, 0)}
        )

    return {
        "open_positions": open_positions,
        "active_applications": active_applications,
        "interviews_scheduled_this_week": interviews_scheduled_this_week,
        "hires_this_month": hires_this_month,
        "by_opening": by_opening,
        "by_stage": by_stage,
        "applications_per_week": applications_per_week,
    }
