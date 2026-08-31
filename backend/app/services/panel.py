"""
Business logic for the interview panel (README goal 5): assigning and
unassigning interviewers on an application, and each interviewer's own
"my assignments" list. The scoping in list_applications_for_interviewer and
get_application_for_interviewer_or_404 is always driven by the
authenticated User the router hands in — never a client-supplied id — so
an interviewer can only ever see their own panel.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models import Application, ApplicationInterviewer, User, UserRole


def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return user


def list_interviewers(db: Session) -> list[User]:
    return db.query(User).filter(User.role == UserRole.INTERVIEWER).order_by(User.name).all()


def list_panel(db: Session, application_id: int) -> list[User]:
    return (
        db.query(User)
        .join(ApplicationInterviewer, ApplicationInterviewer.interviewer_id == User.id)
        .filter(ApplicationInterviewer.application_id == application_id)
        .order_by(User.name)
        .all()
    )


def assign_interviewer(db: Session, application: Application, interviewer_id: int) -> list[User]:
    interviewer = _get_user_or_404(db, interviewer_id)
    if interviewer.role != UserRole.INTERVIEWER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only users with the interviewer role can be assigned to a panel.",
        )

    already_assigned = (
        db.query(ApplicationInterviewer)
        .filter(
            ApplicationInterviewer.application_id == application.id,
            ApplicationInterviewer.interviewer_id == interviewer_id,
        )
        .first()
    )
    if already_assigned is None:
        db.add(ApplicationInterviewer(application_id=application.id, interviewer_id=interviewer_id))
        db.commit()

    return list_panel(db, application.id)


def unassign_interviewer(db: Session, application: Application, interviewer_id: int) -> list[User]:
    assignment = (
        db.query(ApplicationInterviewer)
        .filter(
            ApplicationInterviewer.application_id == application.id,
            ApplicationInterviewer.interviewer_id == interviewer_id,
        )
        .first()
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="That interviewer is not assigned to this application.",
        )

    db.delete(assignment)
    db.commit()
    return list_panel(db, application.id)


def list_applications_for_interviewer(db: Session, interviewer: User) -> list[Application]:
    return (
        db.query(Application)
        .join(ApplicationInterviewer, ApplicationInterviewer.application_id == Application.id)
        .filter(ApplicationInterviewer.interviewer_id == interviewer.id)
        .options(joinedload(Application.job_opening))
        .order_by(Application.stage_changed_at.desc())
        .all()
    )


def get_application_for_interviewer_or_404(
    db: Session, application_id: int, interviewer: User
) -> Application:
    """
    404s both when the application doesn't exist and when it exists but
    this interviewer isn't on its panel, so the response can't be used to
    probe which applications exist elsewhere in the system.
    """
    application = (
        db.query(Application)
        .join(ApplicationInterviewer, ApplicationInterviewer.application_id == Application.id)
        .filter(
            Application.id == application_id,
            ApplicationInterviewer.interviewer_id == interviewer.id,
        )
        .first()
    )
    if application is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    return application
