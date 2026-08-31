"""
Business logic for applications (README goal 3). Every application starts
in Stage.APPLIED, and creation writes a CREATED history entry in the same
transaction as the insert — goal 9's timeline requires every application to
show when it was created, and this is the only code path that ever inserts
one, so there's nowhere else that row could come from.
"""
from fastapi import HTTPException, status
from sqlalchemy import case, or_
from sqlalchemy.orm import Session, joinedload

from app.models import (
    TERMINAL_STAGES,
    Application,
    ApplicationHistoryEntry,
    HistoryEventType,
    JobOpening,
    Stage,
    User,
)
from app.schemas.applications import ApplicationCreate, ApplicationSort, ApplicationUpdate

# Pipeline position, not alphabetical — see ApplicationSort's docstring and
# docs/decisions.md. Rejected has no natural pipeline position; sorted last.
# Written as (condition, value) pairs rather than case({...}, value=col) —
# the dict form loses the column's Postgres ENUM type on the bound
# parameters and psycopg2 rejects them ("invalid input value for enum").
_STAGE_SORT_RANK = case(
    (Application.current_stage == Stage.APPLIED, 0),
    (Application.current_stage == Stage.SCREENING, 1),
    (Application.current_stage == Stage.INTERVIEW, 2),
    (Application.current_stage == Stage.OFFER, 3),
    (Application.current_stage == Stage.HIRED, 4),
    (Application.current_stage == Stage.REJECTED, 5),
)

_SORT_COLUMNS = {
    "applied_date": Application.created_at,
    "stage": _STAGE_SORT_RANK,
    "last_update": Application.updated_at,
}


def _sort_clause(sort: ApplicationSort):
    descending = sort.value.startswith("-")
    column = _SORT_COLUMNS[sort.value[1:] if descending else sort.value]
    return column.desc() if descending else column.asc()


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


def list_applications(
    db: Session,
    *,
    search: str | None,
    job_opening_id: int | None,
    stage: Stage | None,
    source: str | None,
    sort: ApplicationSort,
    page: int,
    page_size: int,
) -> tuple[list[Application], int]:
    """
    Cross-opening search/filter/sort/pagination (README goal 6). Every
    piece of this — the text search, each filter, the sort, and the page
    slice — happens in the SQL query itself; nothing is loaded into Python
    and filtered there.
    """
    query = db.query(Application)

    if search:
        pattern = f"%{search}%"
        query = query.filter(
            or_(
                Application.candidate_name.ilike(pattern),
                Application.candidate_email.ilike(pattern),
            )
        )
    if job_opening_id is not None:
        query = query.filter(Application.job_opening_id == job_opening_id)
    if stage is not None:
        query = query.filter(Application.current_stage == stage)
    if source:
        query = query.filter(Application.source.ilike(source))

    total = query.count()

    results = (
        query.order_by(_sort_clause(sort))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return results, total


def add_feedback(
    db: Session, application: Application, feedback_text: str, actor: User
) -> ApplicationHistoryEntry:
    """
    README goal 9: interviewer feedback is part of the append-only
    timeline, not a field on Application — this is the only code path that
    ever inserts a FEEDBACK entry, and there is deliberately no update or
    delete path for it.
    """
    entry = ApplicationHistoryEntry(
        application_id=application.id,
        event_type=HistoryEventType.FEEDBACK,
        old_stage=None,
        new_stage=None,
        feedback_text=feedback_text,
        actor_id=actor.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_history_for_application(db: Session, application_id: int) -> list[ApplicationHistoryEntry]:
    return (
        db.query(ApplicationHistoryEntry)
        .options(joinedload(ApplicationHistoryEntry.actor))
        .filter(ApplicationHistoryEntry.application_id == application_id)
        .order_by(ApplicationHistoryEntry.created_at.asc(), ApplicationHistoryEntry.id.asc())
        .all()
    )


def list_applications_for_export(db: Session) -> list[Application]:
    """
    README goal 7's CSV export: every application NOT in a terminal stage
    (current_stage not in TERMINAL_STAGES == {HIRED, REJECTED}) — resolved
    in CLAUDE.md, not reinterpreted here — regardless of whether its job
    opening is open, closed, or archived.
    """
    return (
        db.query(Application)
        .options(joinedload(Application.job_opening))
        .filter(Application.current_stage.notin_(TERMINAL_STAGES))
        .order_by(Application.created_at.asc())
        .all()
    )
