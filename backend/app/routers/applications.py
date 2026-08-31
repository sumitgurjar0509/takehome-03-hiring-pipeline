"""
Two routers: one nested under a job opening (create + "show its
applications"), one flat by application id (get/edit) since later goals
(4, 5, 9) need to address a single application without knowing its
opening. Every endpoint here is recruiter-only — interviewers have had no
application-level access since goal 1's role split, and that doesn't
change until goal 5 gives them their one assignment-scoped endpoint.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_recruiter
from app.models import User
from app.schemas.applications import ApplicationCreate, ApplicationOut, ApplicationUpdate
from app.services import applications as applications_service

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


@applications_router.get("/{application_id}", response_model=ApplicationOut)
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return applications_service.get_application_or_404(db, application_id)


@applications_router.patch("/{application_id}", response_model=ApplicationOut)
def update_application(
    application_id: int,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return applications_service.update_application(db, application_id, payload)
