"""
Stalled-application alerts (README goal 10). An application is stalled if
it's sat in current_stage for more than ten days and that stage isn't
terminal. The reappearance rule is nothing but comparing
stall_dismissed_stage to current_stage at query time — goal 4's transition
logic already clears both stall_dismissed_at and stall_dismissed_stage on
every advance/reject/reinstate, so a dismissal only ever matches the exact
stage it was made for. No new state lives here; see docs/decisions.md for
the full reasoning, including the reject-then-reinstate case.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models import TERMINAL_STAGES, Application

STALL_THRESHOLD = timedelta(days=10)


def list_stalled_applications(db: Session) -> list[Application]:
    threshold = datetime.now(timezone.utc) - STALL_THRESHOLD
    return (
        db.query(Application)
        .options(joinedload(Application.job_opening))
        .filter(
            Application.current_stage.notin_(TERMINAL_STAGES),
            Application.stage_changed_at < threshold,
            or_(
                Application.stall_dismissed_at.is_(None),
                Application.stall_dismissed_stage != Application.current_stage,
            ),
        )
        .order_by(Application.stage_changed_at.asc())
        .all()
    )


def dismiss_alert(db: Session, application: Application) -> Application:
    application.stall_dismissed_at = datetime.now(timezone.utc)
    application.stall_dismissed_stage = application.current_stage
    db.commit()
    db.refresh(application)
    return application
