"""
Pipeline stage transitions (README goal 4) — the core business logic of the
whole app. advance() / reject() / reinstate() each take an Application and
mutate it in place according to one of the three legal transition types,
returning the ApplicationHistoryEntry to persist. They raise PipelineError
on any illegal move and deliberately do no db.add() / db.commit() — the
caller owns the transaction boundary.

bulk_advance() / bulk_reject() (goal 7) are that caller for a whole batch:
they call advance()/reject() per application, commit each success
immediately, and turn each PipelineError into its own failed result rather
than aborting the batch — one ineligible application never blocks the
others.
"""
from sqlalchemy.orm import Session

from app.models import (
    STAGE_ORDER,
    Application,
    ApplicationHistoryEntry,
    HistoryEventType,
    Stage,
    User,
    utcnow,
)
from app.schemas.applications import BulkActionResultItem


class PipelineError(Exception):
    """Raised for any illegal transition attempt. The message is user-facing."""


def next_stage_after(stage: Stage) -> Stage | None:
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

    expected_next = next_stage_after(current)
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


def bulk_advance(db: Session, application_ids: list[int], actor: User) -> list[BulkActionResultItem]:
    """
    README goal 7's bulk advance. Reuses advance() per application rather
    than reimplementing any rule — an application ineligible to move
    (skips, Hired, Rejected) never fails the batch, it just gets its own
    failed result with advance()'s own message. Each success commits
    immediately so partial progress survives a later item's failure.
    """
    results = []
    for application_id in application_ids:
        application = db.get(Application, application_id)
        if application is None:
            results.append(
                BulkActionResultItem(
                    application_id=application_id, success=False, message="Application not found."
                )
            )
            continue

        # advance() itself re-derives and validates the next stage; this is
        # just what we pass in as the candidate target for the eligible
        # case. For Hired/Rejected, advance() raises before ever looking at
        # to_stage, so the placeholder value here is never actually used.
        target = next_stage_after(application.current_stage) or application.current_stage
        try:
            history_entry = advance(application, target, actor)
        except PipelineError as exc:
            results.append(
                BulkActionResultItem(application_id=application_id, success=False, message=str(exc))
            )
            continue

        db.add(history_entry)
        db.commit()
        results.append(
            BulkActionResultItem(
                application_id=application_id,
                success=True,
                message=f"Advanced to {_label(target)}.",
            )
        )
    return results


def bulk_reject(db: Session, application_ids: list[int], actor: User) -> list[BulkActionResultItem]:
    """README goal 7's bulk reject. Same shape as bulk_advance, reusing reject()."""
    results = []
    for application_id in application_ids:
        application = db.get(Application, application_id)
        if application is None:
            results.append(
                BulkActionResultItem(
                    application_id=application_id, success=False, message="Application not found."
                )
            )
            continue

        try:
            history_entry = reject(application, actor)
        except PipelineError as exc:
            results.append(
                BulkActionResultItem(application_id=application_id, success=False, message=str(exc))
            )
            continue

        db.add(history_entry)
        db.commit()
        results.append(
            BulkActionResultItem(application_id=application_id, success=True, message="Rejected.")
        )
    return results
