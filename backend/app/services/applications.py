"""
Business logic for applications (README goal 3). Every application starts
in Stage.APPLIED, and creation writes a CREATED history entry in the same
transaction as the insert — goal 9's timeline requires every application to
show when it was created, and this is the only code path that ever inserts
one, so there's nowhere else that row could come from.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import (
    Application,
    ApplicationHistoryEntry,
    HistoryEventType,
    JobOpening,
    Stage,
    User,
)
from app.schemas.applications import ApplicationCreate, ApplicationUpdate


def get_opening_or_404(db: Session, opening_id: int) -> JobOpening:
    opening = db.get(JobOpening, opening_id)
    if opening is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job opening not found.")
    return opening


def create_application(
    db: Session, opening_id: int, data: ApplicationCreate, created_by: User
) -> Application:
    get_opening_or_404(db, opening_id)
    application = Application(
        job_opening_id=opening_id,
        candidate_name=data.candidate_name,
        candidate_email=data.candidate_email,
        source=data.source,
        notes=data.notes,
        current_stage=Stage.APPLIED,
        created_by_id=created_by.id,
    )
    db.add(application)
    db.flush()  # assigns application.id so the history row can reference it

    db.add(
        ApplicationHistoryEntry(
            application_id=application.id,
            event_type=HistoryEventType.CREATED,
            old_stage=None,
            new_stage=Stage.APPLIED,
            actor_id=created_by.id,
        )
    )
    db.commit()
    db.refresh(application)
    return application


def list_applications_for_opening(db: Session, opening_id: int) -> list[Application]:
    get_opening_or_404(db, opening_id)
    return (
        db.query(Application)
        .filter(Application.job_opening_id == opening_id)
        .order_by(Application.created_at.desc())
        .all()
    )


def get_application_or_404(db: Session, application_id: int) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    return application


def update_application(db: Session, application_id: int, data: ApplicationUpdate) -> Application:
    application = get_application_or_404(db, application_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(application, field, value)
    db.commit()
    db.refresh(application)
    return application
