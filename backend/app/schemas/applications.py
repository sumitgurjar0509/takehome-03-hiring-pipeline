from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import Stage
from app.schemas.auth import validate_email_format


class ApplicationCreate(BaseModel):
    candidate_name: str
    candidate_email: str
    source: str = ""
    notes: str = ""

    @field_validator("candidate_name")
    @classmethod
    def _check_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Candidate name cannot be blank.")
        return v

    @field_validator("candidate_email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        return validate_email_format(v)


class ApplicationUpdate(BaseModel):
    candidate_name: str | None = None
    candidate_email: str | None = None
    source: str | None = None
    notes: str | None = None

    @field_validator("candidate_name")
    @classmethod
    def _check_name(cls, v: str | None) -> str | None:
        if v is None:
            return v
        v = v.strip()
        if not v:
            raise ValueError("Candidate name cannot be blank.")
        return v

    @field_validator("candidate_email")
    @classmethod
    def _check_email(cls, v: str | None) -> str | None:
        return v if v is None else validate_email_format(v)


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    job_opening_id: int
    candidate_name: str
    candidate_email: str
    source: str
    notes: str
    current_stage: Stage
    rejected_from_stage: Stage | None
    created_by_id: int
    created_at: datetime
    updated_at: datetime
