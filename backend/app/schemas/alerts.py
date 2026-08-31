from datetime import datetime

from pydantic import BaseModel

from app.models import Stage


class StalledApplicationOut(BaseModel):
    id: int
    job_opening_id: int
    job_opening_title: str
    candidate_name: str
    candidate_email: str
    current_stage: Stage
    stage_changed_at: datetime
