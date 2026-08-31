"""
ORM models. See docs/schema.md for the full write-up of relationships,
constraints and the reasoning behind each one; this file is the source of
truth for what actually got built.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- Enums -------------------------------------------------------------
# Stored as native Postgres ENUM types via SQLAlchemy's Enum, so illegal
# values are rejected by the database itself, not just application code.

class UserRole(str, enum.Enum):
    RECRUITER = "recruiter"
    INTERVIEWER = "interviewer"


class OpeningStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class Stage(str, enum.Enum):
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"


# The forward order of the pipeline. REJECTED is reachable from any of
# these but is not itself part of the forward sequence.
STAGE_ORDER: list[Stage] = [
    Stage.APPLIED,
    Stage.SCREENING,
    Stage.INTERVIEW,
    Stage.OFFER,
    Stage.HIRED,
]

TERMINAL_STAGES = {Stage.HIRED, Stage.REJECTED}


class HistoryEventType(str, enum.Enum):
    CREATED = "created"
    STAGE_CHANGE = "stage_change"
    REJECTED = "rejected"
    REINSTATED = "reinstated"
    FEEDBACK = "feedback"


# --- Models --------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    opened_job_openings: Mapped[list["JobOpening"]] = relationship(back_populates="created_by")
    interviewer_assignments: Mapped[list["ApplicationInterviewer"]] = relationship(back_populates="interviewer")


class JobOpening(Base):
    __tablename__ = "job_openings"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[OpeningStatus] = mapped_column(
        Enum(OpeningStatus, name="opening_status"), nullable=False, default=OpeningStatus.OPEN
    )
    # Archiving is deliberately separate from status: status describes whether the
    # position is actively hiring, archived controls default-view visibility without
    # destroying the opening's applications. See docs/decisions.md.
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    created_by: Mapped["User"] = relationship(back_populates="opened_job_openings")
    applications: Mapped[list["Application"]] = relationship(back_populates="job_opening")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_opening_id: Mapped[int] = mapped_column(ForeignKey("job_openings.id"), nullable=False, index=True)
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    candidate_email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")

    current_stage: Mapped[Stage] = mapped_column(
        Enum(Stage, name="application_stage"), nullable=False, default=Stage.APPLIED, index=True
    )
    # Set only while current_stage == REJECTED; records the exact stage to return
    # to on reinstatement, per README goal 4 ("not reset to Applied").
    rejected_from_stage: Mapped[Stage | None] = mapped_column(
        Enum(Stage, name="application_stage"), nullable=True
    )
    # Timestamp of the most recent stage transition. Drives the stalled-alert
    # calculation (goal 10) — indexed because that query scans on it.
    stage_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    # Stalled-alert dismissal state lives directly on the application rather than
    # in a separate table (see docs/decisions.md). A dismissal is only valid for
    # the stage it was made at — if current_stage no longer matches
    # stall_dismissed_stage, the dismissal is stale and the alert can reappear,
    # which is exactly the reappearance rule in goal 10.
    stall_dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    stall_dismissed_stage: Mapped[Stage | None] = mapped_column(
        Enum(Stage, name="application_stage"), nullable=True
    )

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    job_opening: Mapped["JobOpening"] = relationship(back_populates="applications")
    interviewers: Mapped[list["ApplicationInterviewer"]] = relationship(
        back_populates="application", cascade="all, delete-orphan"
    )
    history: Mapped[list["ApplicationHistoryEntry"]] = relationship(
        back_populates="application", order_by="ApplicationHistoryEntry.created_at"
    )

    __table_args__ = (
        # Supports "applications in opening X currently at stage Y" without a full scan.
        Index("ix_applications_opening_stage", "job_opening_id", "current_stage"),
    )


class ApplicationInterviewer(Base):
    """Many-to-many join: any interviewer can be on any number of application panels."""

    __tablename__ = "application_interviewers"

    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), primary_key=True)
    interviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True, index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    application: Mapped["Application"] = relationship(back_populates="interviewers")
    interviewer: Mapped["User"] = relationship(back_populates="interviewer_assignments")


class ApplicationHistoryEntry(Base):
    """
    Immutable, append-only timeline (README goal 9). No route ever updates or
    deletes a row here — enforced by simply never writing UPDATE/DELETE
    against this table anywhere in the codebase (see docs/schema.md for why
    this is enforced in application code rather than a DB trigger).
    """

    __tablename__ = "application_history_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    application_id: Mapped[int] = mapped_column(ForeignKey("applications.id"), nullable=False, index=True)
    event_type: Mapped[HistoryEventType] = mapped_column(
        Enum(HistoryEventType, name="history_event_type"), nullable=False
    )
    old_stage: Mapped[Stage | None] = mapped_column(Enum(Stage, name="application_stage"), nullable=True)
    new_stage: Mapped[Stage | None] = mapped_column(Enum(Stage, name="application_stage"), nullable=True)
    feedback_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    application: Mapped["Application"] = relationship(back_populates="history")
    actor: Mapped["User"] = relationship()

    __table_args__ = (
        Index("ix_history_application_created", "application_id", "created_at"),
    )
