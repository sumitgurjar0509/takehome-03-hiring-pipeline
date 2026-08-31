"""
Two routers: one nested under a job opening (create + "show its
applications"), one flat by application id (get/edit) since later goals
(4, 5, 9) need to address a single application without knowing its
opening. Every write here is recruiter-only. GET /{application_id} is the
one exception, as of goal 5: a recruiter can fetch any application, and an
interviewer can fetch one only if they're on its panel (404 otherwise) —
the first and only application-level access interviewers get, scoped
server-side via the join table rather than loosened wholesale. GET
"" (goal 6) is the recruiter-scoped cross-opening search/filter/sort/
paginate list — separate from goal 5's /my-assignments, which is
interviewer-panel-scoped and stays that way. GET /export and POST /bulk
(goal 7) are registered before GET /{application_id} — same HTTP method,
literal path segment, so registration order decides the match.
"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_interviewer, require_recruiter
from app.models import Stage, User, UserRole
from app.schemas.applications import (
    AdvanceRequest,
    ApplicationCreate,
    ApplicationListOut,
    ApplicationOut,
    ApplicationSort,
    ApplicationUpdate,
    BulkAction,
    BulkActionRequest,
    BulkActionResponse,
)
from app.schemas.history import FeedbackCreate, HistoryEntryOut
from app.services import applications as applications_service
from app.services import panel as panel_service
from app.services import pipeline as pipeline_service
from app.services.pipeline import PipelineError

opening_applications_router = APIRouter(
    prefix="/openings/{opening_id}/applications", tags=["applications"]
)
applications_router = APIRouter(prefix="/applications", tags=["applications"])


@opening_applications_router.post("", response_model=ApplicationOut, status_code=201)
def create_application(
    opening_id: int,
    payload: ApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return applications_service.create_application(db, opening_id, payload, current_user)


@opening_applications_router.get("", response_model=list[ApplicationOut])
def list_applications_for_opening(
    opening_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return applications_service.list_applications_for_opening(db, opening_id)


@applications_router.get("", response_model=ApplicationListOut)
def list_applications(
    search: str | None = None,
    job_opening_id: int | None = None,
    stage: Stage | None = None,
    source: str | None = None,
    sort: ApplicationSort = ApplicationSort.APPLIED_DATE_DESC,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    results, total = applications_service.list_applications(
        db,
        search=search,
        job_opening_id=job_opening_id,
        stage=stage,
        source=source,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    return ApplicationListOut(results=results, total=total, page=page, page_size=page_size)


@applications_router.get("/export")
def export_applications(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    applications = applications_service.list_applications_for_export(db)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Candidate Name", "Candidate Email", "Job Opening", "Stage", "Applied Date"])
    for application in applications:
        writer.writerow(
            [
                application.candidate_name,
                application.candidate_email,
                application.job_opening.title,
                application.current_stage.value.capitalize(),
                application.created_at.strftime("%Y-%m-%d"),
            ]
        )

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=applications.csv"},
    )


@applications_router.post("/bulk", response_model=BulkActionResponse)
def bulk_action(
    payload: BulkActionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    if payload.action == BulkAction.ADVANCE:
        results = pipeline_service.bulk_advance(db, payload.application_ids, current_user)
    else:
        results = pipeline_service.bulk_reject(db, payload.application_ids, current_user)
    return BulkActionResponse(results=results)


@applications_router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.INTERVIEWER:
        return panel_service.get_application_for_interviewer_or_404(db, application_id, current_user)
    return applications_service.get_application_or_404(db, application_id)


def _to_history_entry_out(entry) -> HistoryEntryOut:
    return HistoryEntryOut(
        id=entry.id,
        event_type=entry.event_type,
        old_stage=entry.old_stage,
        new_stage=entry.new_stage,
        feedback_text=entry.feedback_text,
        actor_id=entry.actor_id,
        actor_name=entry.actor.name,
        created_at=entry.created_at,
    )


@applications_router.get("/{application_id}/history", response_model=list[HistoryEntryOut])
def get_application_history(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Same recruiter-any / interviewer-only-if-assigned split as GET
    # /{application_id} — 404 (not 403) for an interviewer's unassigned
    # application, consistent with that existing read.
    if current_user.role == UserRole.INTERVIEWER:
        panel_service.get_application_for_interviewer_or_404(db, application_id, current_user)
    else:
        applications_service.get_application_or_404(db, application_id)

    entries = applications_service.list_history_for_application(db, application_id)
    return [_to_history_entry_out(entry) for entry in entries]


@applications_router.post("/{application_id}/feedback", response_model=HistoryEntryOut, status_code=201)
def add_feedback(
    application_id: int,
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_interviewer),
):
    # Feedback is interviewer-only (README goal 1) and scoped to the
    # interviewer's own panel — 403 here rather than the 404 used for GET
    # reads, since this is a write action and the interviewer already
    # knows the application id from their own assignment history.
    application = panel_service.get_application_for_interviewer_or_403(db, application_id, current_user)
    entry = applications_service.add_feedback(db, application, payload.feedback_text, current_user)
    return _to_history_entry_out(entry)


@applications_router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return applications_service.update_application(db, application_id, payload)


def _apply_transition(db: Session, history_entry) -> None:
    db.add(history_entry)
    db.commit()


@applications_router.post("/{application_id}/advance", response_model=ApplicationOut)
def advance_application(
    application_id: int,
    payload: AdvanceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    application = applications_service.get_application_or_404(db, application_id)
    try:
        history_entry = pipeline_service.advance(application, payload.to_stage, current_user)
    except PipelineError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    _apply_transition(db, history_entry)
    db.refresh(application)
    return application


@applications_router.post("/{application_id}/reject", response_model=ApplicationOut)
def reject_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    application = applications_service.get_application_or_404(db, application_id)
    try:
        history_entry = pipeline_service.reject(application, current_user)
    except PipelineError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    _apply_transition(db, history_entry)
    db.refresh(application)
    return application


@applications_router.post("/{application_id}/reinstate", response_model=ApplicationOut)
def reinstate_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    application = applications_service.get_application_or_404(db, application_id)
    try:
        history_entry = pipeline_service.reinstate(application, current_user)
    except PipelineError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    _apply_transition(db, history_entry)
    db.refresh(application)
    return application
