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
interviewer-panel-scoped and stays that way.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_recruiter
from app.models import Stage, User, UserRole
from app.schemas.applications import (
    AdvanceRequest,
    ApplicationCreate,
    ApplicationListOut,
    ApplicationOut,
    ApplicationSort,
    ApplicationUpdate,
)
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


@applications_router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.INTERVIEWER:
        return panel_service.get_application_for_interviewer_or_404(db, application_id, current_user)
    return applications_service.get_application_or_404(db, application_id)


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
