"""
Business logic for job openings (README goal 2). Archive/restore and the
default-view filtering live here rather than in the router, and the
`include_archived` query param this exposes is the pattern goal 6's
applications search/filter reuses rather than inventing a second one.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import JobOpening, User
from app.schemas.openings import JobOpeningCreate, JobOpeningUpdate


def create_opening(db: Session, data: JobOpeningCreate, created_by: User) -> JobOpening:
    opening = JobOpening(
        title=data.title,
        department=data.department,
        description=data.description,
        status=data.status,
        created_by_id=created_by.id,
    )
    db.add(opening)
    db.commit()
    db.refresh(opening)
    return opening


def list_openings(db: Session, *, include_archived: bool) -> list[JobOpening]:
    query = db.query(JobOpening)
    if not include_archived:
        query = query.filter(JobOpening.archived.is_(False))
    return query.order_by(JobOpening.created_at.desc()).all()


def get_opening_or_404(db: Session, opening_id: int) -> JobOpening:
    opening = db.get(JobOpening, opening_id)
    if opening is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job opening not found.")
    return opening


def update_opening(db: Session, opening_id: int, data: JobOpeningUpdate) -> JobOpening:
    opening = get_opening_or_404(db, opening_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(opening, field, value)
    db.commit()
    db.refresh(opening)
    return opening


def archive_opening(db: Session, opening_id: int) -> JobOpening:
    # Archiving only ever hides the opening from default views (see
    # docs/decisions.md) — it never touches the opening's applications.
    opening = get_opening_or_404(db, opening_id)
    opening.archived = True
    db.commit()
    db.refresh(opening)
    return opening


def restore_opening(db: Session, opening_id: int) -> JobOpening:
    opening = get_opening_or_404(db, opening_id)
    opening.archived = False
    db.commit()
    db.refresh(opening)
    return opening
