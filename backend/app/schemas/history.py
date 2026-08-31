from datetime import datetime

from pydantic import BaseModel, field_validator

from app.models import HistoryEventType, Stage


class FeedbackCreate(BaseModel):
    feedback_text: str

    @field_validator("feedback_text")
    @classmethod
    def _check_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Feedback text cannot be blank.")
        return v


class HistoryEntryOut(BaseModel):
    id: int
    event_type: HistoryEventType
    old_stage: Stage | None
    new_stage: Stage | None
    feedback_text: str | None
    actor_id: int
    actor_name: str
    created_at: datetime
