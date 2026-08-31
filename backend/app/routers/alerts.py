from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_recruiter
from app.models import User
from app.schemas.alerts import StalledApplicationOut
from app.services import alerts as alerts_service

router = APIRouter(tags=["alerts"])


@router.get("/alerts", response_model=list[StalledApplicationOut])
def list_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_recruiter),
):
    applications = alerts_service.list_stalled_applications(db)
    return [
        StalledApplicationOut(
            id=application.id,
            job_opening_id=application.job_opening_id,
            job_opening_title=application.job_opening.title,
            candidate_name=application.candidate_name,
            candidate_email=application.candidate_email,
            current_stage=application.current_stage,
            stage_changed_at=application.stage_changed_at,
        )
        for application in applications
    ]
