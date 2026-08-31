"""
Pipeline stage transitions (README goal 4) — the core business logic of the
whole app. Each function takes an Application and mutates it in place
according to one of the three legal transition types, returning the
ApplicationHistoryEntry to persist. Raises PipelineError on any illegal
move; the caller turns that into a 4xx (a single-application router
endpoint) or a per-candidate failure entry (goal 7's bulk actions), without
this module knowing or caring which.

Deliberately does no db.add() / db.commit() here — the caller owns the
transaction boundary. That's what lets goal 7 report partial success across
a batch: each application's transition can be attempted, and failures left
uncommitted, independently of the others.
"""
from app.models import (
    STAGE_ORDER,
    Application,
    ApplicationHistoryEntry,
    HistoryEventType,
    Stage,
    User,
    utcnow,
)


class PipelineError(Exception):
    """Raised for any illegal transition attempt. The message is user-facing."""


def _next_stage(stage: Stage) -> Stage | None:
    if stage not in STAGE_ORDER:
        return None
    index = STAGE_ORDER.index(stage)
    if index + 1 >= len(STAGE_ORDER):
        return None
    return STAGE_ORDER[index + 1]


def _label(stage: Stage) -> str:
    return stage.value.capitalize()


def _record_transition(application: Application) -> None:
    # Every transition that changes current_stage — advance, reject, and
    # reinstate — resets the stall clock and clears any dismissal, since a
    # dismissal only ever applies to the stage it was made at (goal 10).
    application.stage_changed_at = utcnow()
    application.stall_dismissed_at = None
    application.stall_dismissed_stage = None


def advance(application: Application, to_stage: Stage, actor: User) -> ApplicationHistoryEntry:
    current = application.current_stage

    if current == Stage.REJECTED:
        raise PipelineError(
            "Cannot advance a rejected application — reinstate it before moving it forward."
        )
    if current == Stage.HIRED:
        raise PipelineError("Cannot advance: this application is already Hired, a final stage.")

    expected_next = _next_stage(current)
    if expected_next is None or to_stage != expected_next:
        raise PipelineError(
            f"Cannot advance from {_label(current)} to {_label(to_stage)} — "
            f"the only valid next stage is {_label(expected_next)}."
        )

    old_stage = current
    application.current_stage = expected_next
    _record_transition(application)

    return ApplicationHistoryEntry(
        application_id=application.id,
        event_type=HistoryEventType.STAGE_CHANGE,
        old_stage=old_stage,
        new_stage=expected_next,
        actor_id=actor.id,
    )


def reject(application: Application, actor: User) -> ApplicationHistoryEntry:
    current = application.current_stage

    if current == Stage.REJECTED:
        raise PipelineError("This application is already rejected.")
    if current == Stage.HIRED:
        raise PipelineError("A hired application cannot be rejected.")

    old_stage = current
    application.rejected_from_stage = current
    application.current_stage = Stage.REJECTED
    _record_transition(application)

    return ApplicationHistoryEntry(
        application_id=application.id,
        event_type=HistoryEventType.REJECTED,
        old_stage=old_stage,
        new_stage=Stage.REJECTED,
        actor_id=actor.id,
    )


def reinstate(application: Application, actor: User) -> ApplicationHistoryEntry:
    if application.current_stage != Stage.REJECTED:
        raise PipelineError("Only a rejected application can be reinstated.")

    old_stage = application.current_stage
    target_stage = application.rejected_from_stage
    application.current_stage = target_stage
    application.rejected_from_stage = None
    _record_transition(application)

    return ApplicationHistoryEntry(
        application_id=application.id,
        event_type=HistoryEventType.REINSTATED,
        old_stage=old_stage,
        new_stage=target_stage,
        actor_id=actor.id,
    )
