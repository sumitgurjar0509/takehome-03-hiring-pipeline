from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import Stage


class InterviewerAssignmentCreate(BaseModel):
    interviewer_id: int


class MyAssignmentOut(BaseModel):
    """
    What an interviewer sees on their "My Assignments" list — an
    Application's fields plus the job opening's title, since goal 3's
    ApplicationOut only carries job_opening_id and this view needs to be
    readable without a second round trip per row.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_opening_id: int
    job_opening_title: str
    candidate_name: str
    candidate_email: str
    source: str
    current_stage: Stage
    stage_changed_at: datetime
