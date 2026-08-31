from datetime import date

from pydantic import BaseModel

from app.models import Stage


class OpeningBreakdownItem(BaseModel):
    job_opening_id: int
    job_opening_title: str
    count: int


class StageBreakdownItem(BaseModel):
    stage: Stage
    count: int


class WeeklyApplicationsItem(BaseModel):
    week_start: date
    count: int


class DashboardOut(BaseModel):
    open_positions: int
    active_applications: int
    interviews_scheduled_this_week: int
    hires_this_month: int
    by_opening: list[OpeningBreakdownItem]
    by_stage: list[StageBreakdownItem]
    applications_per_week: list[WeeklyApplicationsItem]
