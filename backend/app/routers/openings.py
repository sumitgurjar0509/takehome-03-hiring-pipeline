from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_recruiter
from app.models import User
from app.schemas.openings import JobOpeningCreate, JobOpeningOut, JobOpeningUpdate
from app.services import openings as openings_service

router = APIRouter(prefix="/openings", tags=["openings"])


@router.post("", response_model=JobOpeningOut, status_code=201)
def create_opening(
    payload: JobOpeningCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return openings_service.create_opening(db, payload, current_user)


@router.get("", response_model=list[JobOpeningOut])
def list_openings(
    include_archived: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return openings_service.list_openings(db, include_archived=include_archived)


@router.get("/{opening_id}", response_model=JobOpeningOut)
def get_opening(
    opening_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return openings_service.get_opening_or_404(db, opening_id)


@router.patch("/{opening_id}", response_model=JobOpeningOut)
def update_opening(
    opening_id: int,
    payload: JobOpeningUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return openings_service.update_opening(db, opening_id, payload)


@router.post("/{opening_id}/archive", response_model=JobOpeningOut)
def archive_opening(
    opening_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return openings_service.archive_opening(db, opening_id)


@router.post("/{opening_id}/restore", response_model=JobOpeningOut)
def restore_opening(
    opening_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    return openings_service.restore_opening(db, opening_id)
