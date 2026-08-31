from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import OpeningStatus


def _require_non_blank(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("This field cannot be blank.")
    return value


class JobOpeningCreate(BaseModel):
    title: str
    department: str
    description: str = ""
    status: OpeningStatus = OpeningStatus.OPEN

    @field_validator("title", "department")
    @classmethod
    def _check_not_blank(cls, v: str) -> str:
        return _require_non_blank(v)


class JobOpeningUpdate(BaseModel):
    title: str | None = None
    department: str | None = None
    description: str | None = None
    status: OpeningStatus | None = None

    @field_validator("title", "department")
    @classmethod
    def _check_not_blank(cls, v: str | None) -> str | None:
        return v if v is None else _require_non_blank(v)


class JobOpeningOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    department: str
    description: str
    status: OpeningStatus
    archived: bool
    created_by_id: int
    created_at: datetime
    updated_at: datetime
