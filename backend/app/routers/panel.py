"""
Interview panel (README goal 5). Assign/unassign/list-panel and the
interviewer directory lookup are recruiter-only; "my assignments" is
interviewer-only and always resolved from the authenticated user via the
join table, never a client-supplied id.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_interviewer, require_recruiter
from app.models import User
from app.schemas.auth import UserOut
from app.schemas.panel import InterviewerAssignmentCreate, MyAssignmentOut
from app.services import applications as applications_service
from app.services import panel as panel_service

router = APIRouter(tags=["panel"])


@router.get("/interviewers", response_model=list[UserOut])
def list_interviewers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return panel_service.list_interviewers(db)


@router.get("/applications/{application_id}/interviewers", response_model=list[UserOut])
def get_panel(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    applications_service.get_application_or_404(db, application_id)
    return panel_service.list_panel(db, application_id)


@router.post("/applications/{application_id}/interviewers", response_model=list[UserOut])
def assign_interviewer(
    application_id: int,
    payload: InterviewerAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    application = applications_service.get_application_or_404(db, application_id)
    return panel_service.assign_interviewer(db, application, payload.interviewer_id)


@router.delete("/applications/{application_id}/interviewers/{interviewer_id}", response_model=list[UserOut])
def unassign_interviewer(
    application_id: int,
    interviewer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    application = applications_service.get_application_or_404(db, application_id)
    return panel_service.unassign_interviewer(db, application, interviewer_id)


@router.get("/my-assignments", response_model=list[MyAssignmentOut])
def my_assignments(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_interviewer),
):
    applications = panel_service.list_applications_for_interviewer(db, current_user)
    return [
        MyAssignmentOut(
            id=application.id,
            job_opening_id=application.job_opening_id,
            job_opening_title=application.job_opening.title,
            candidate_name=application.candidate_name,
            candidate_email=application.candidate_email,
            source=application.source,
            current_stage=application.current_stage,
            stage_changed_at=application.stage_changed_at,
        )
        for application in applications
    ]
