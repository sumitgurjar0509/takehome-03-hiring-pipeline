from datetime import datetime, timezone

import pytest

from app.models import STAGE_ORDER, ApplicationHistoryEntry, HistoryEventType, Stage
from tests.conftest import auth_headers

ACTIVE_STAGES = [Stage.APPLIED, Stage.SCREENING, Stage.INTERVIEW, Stage.OFFER]


def _next_of(stage: Stage) -> Stage:
    return STAGE_ORDER[STAGE_ORDER.index(stage) + 1]


def _set_application_stage(db_session, application, stage, rejected_from_stage=None):
    application.current_stage = stage
    application.rejected_from_stage = rejected_from_stage
    db_session.commit()
    db_session.refresh(application)


def _stale_dismissal(db_session, application, stage):
    """Simulate a recruiter having dismissed a stall alert at this stage in
    the past, so tests can assert the transition logic actually clears it."""
    application.stall_dismissed_at = datetime(2020, 1, 1, tzinfo=timezone.utc)
    application.stall_dismissed_stage = stage
    db_session.commit()
    db_session.refresh(application)


def _latest_history_entry(db_session, application_id):
    return (
        db_session.query(ApplicationHistoryEntry)
        .filter(ApplicationHistoryEntry.application_id == application_id)
        .order_by(ApplicationHistoryEntry.id.desc())
        .first()
    )


# ---- Advance: valid single-step from every stage ----------------------


@pytest.mark.parametrize("current_stage", ACTIVE_STAGES)
def test_advance_moves_exactly_one_step(
    client, recruiter, make_opening, make_application, db_session, current_stage
):
    opening = make_opening()
    application = make_application(opening)
    _set_application_stage(db_session, application, current_stage)
    _stale_dismissal(db_session, application, current_stage)
    stage_changed_at_before = application.stage_changed_at

    next_stage = _next_of(current_stage)
    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        f"/applications/{application.id}/advance",
        json={"to_stage": next_stage.value},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["current_stage"] == next_stage.value
    assert body["rejected_from_stage"] is None

    db_session.refresh(application)
    assert application.current_stage == next_stage
    assert application.stage_changed_at > stage_changed_at_before
    assert application.stall_dismissed_at is None
    assert application.stall_dismissed_stage is None

    entry = _latest_history_entry(db_session, application.id)
    assert entry.event_type == HistoryEventType.STAGE_CHANGE
    assert entry.old_stage == current_stage
    assert entry.new_stage == next_stage
    assert entry.actor_id == recruiter.id


# ---- Advance: illegal skip from every stage, every invalid target -----

ILLEGAL_ADVANCE_CASES = [
    (stage, target, _next_of(stage))
    for stage in ACTIVE_STAGES
    for target in Stage
    if target != _next_of(stage)
]


@pytest.mark.parametrize(
    "current_stage,to_stage,expected_next",
    ILLEGAL_ADVANCE_CASES,
    ids=[f"{c.value}->{t.value}" for c, t, _ in ILLEGAL_ADVANCE_CASES],
)
def test_advance_rejects_illegal_target(
    client,
    recruiter,
    make_opening,
    make_application,
    db_session,
    current_stage,
    to_stage,
    expected_next,
):
    opening = make_opening()
    application = make_application(opening)
    _set_application_stage(db_session, application, current_stage)
    stage_changed_at_before = application.stage_changed_at

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        f"/applications/{application.id}/advance",
        json={"to_stage": to_stage.value},
        headers=headers,
    )
    assert response.status_code == 409, response.text
    expected_message = (
        f"Cannot advance from {current_stage.value.capitalize()} to {to_stage.value.capitalize()} "
        f"— the only valid next stage is {expected_next.value.capitalize()}."
    )
    assert response.json()["detail"] == expected_message

    db_session.refresh(application)
    assert application.current_stage == current_stage
    assert application.stage_changed_at == stage_changed_at_before


@pytest.mark.parametrize("to_stage", list(Stage))
def test_advance_from_hired_always_fails(
    client, recruiter, make_opening, make_application, db_session, to_stage
):
    opening = make_opening()
    application = make_application(opening)
    _set_application_stage(db_session, application, Stage.HIRED)

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        f"/applications/{application.id}/advance",
        json={"to_stage": to_stage.value},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Cannot advance: this application is already Hired, a final stage."


@pytest.mark.parametrize("to_stage", list(Stage))
def test_advance_from_rejected_always_fails(
    client, recruiter, make_opening, make_application, db_session, to_stage
):
    opening = make_opening()
    application = make_application(opening)
    _set_application_stage(db_session, application, Stage.REJECTED, rejected_from_stage=Stage.SCREENING)

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        f"/applications/{application.id}/advance",
        json={"to_stage": to_stage.value},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot advance a rejected application — reinstate it before moving it forward."
    )


# ---- Reject from every active stage ------------------------------------


@pytest.mark.parametrize("current_stage", ACTIVE_STAGES)
def test_reject_from_active_stage_succeeds(
    client, recruiter, make_opening, make_application, db_session, current_stage
):
    opening = make_opening()
    application = make_application(opening)
    _set_application_stage(db_session, application, current_stage)
    _stale_dismissal(db_session, application, current_stage)
    stage_changed_at_before = application.stage_changed_at

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(f"/applications/{application.id}/reject", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["current_stage"] == "rejected"
    assert body["rejected_from_stage"] == current_stage.value

    db_session.refresh(application)
    assert application.current_stage == Stage.REJECTED
    assert application.rejected_from_stage == current_stage
    assert application.stage_changed_at > stage_changed_at_before
    assert application.stall_dismissed_at is None
    assert application.stall_dismissed_stage is None

    entry = _latest_history_entry(db_session, application.id)
    assert entry.event_type == HistoryEventType.REJECTED
    assert entry.old_stage == current_stage
    assert entry.new_stage == Stage.REJECTED
    assert entry.actor_id == recruiter.id


def test_reject_from_hired_fails(client, recruiter, make_opening, make_application, db_session):
    opening = make_opening()
    application = make_application(opening)
    _set_application_stage(db_session, application, Stage.HIRED)
    stage_changed_at_before = application.stage_changed_at

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(f"/applications/{application.id}/reject", headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "A hired application cannot be rejected."

    db_session.refresh(application)
    assert application.current_stage == Stage.HIRED
    assert application.stage_changed_at == stage_changed_at_before


def test_reject_already_rejected_fails(client, recruiter, make_opening, make_application, db_session):
    opening = make_opening()
    application = make_application(opening)
    _set_application_stage(db_session, application, Stage.REJECTED, rejected_from_stage=Stage.INTERVIEW)

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(f"/applications/{application.id}/reject", headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "This application is already rejected."

    db_session.refresh(application)
    assert application.rejected_from_stage == Stage.INTERVIEW


# ---- Reinstate: only valid from REJECTED, restores exact stage --------


@pytest.mark.parametrize("original_stage", ACTIVE_STAGES)
def test_reinstate_restores_exact_rejected_from_stage(
    client, recruiter, make_opening, make_application, db_session, original_stage
):
    opening = make_opening()
    application = make_application(opening)
    _set_application_stage(db_session, application, Stage.REJECTED, rejected_from_stage=original_stage)
    _stale_dismissal(db_session, application, Stage.REJECTED)
    stage_changed_at_before = application.stage_changed_at

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(f"/applications/{application.id}/reinstate", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["current_stage"] == original_stage.value
    assert body["rejected_from_stage"] is None

    db_session.refresh(application)
    assert application.current_stage == original_stage
    assert application.rejected_from_stage is None
    assert application.stage_changed_at > stage_changed_at_before
    assert application.stall_dismissed_at is None
    assert application.stall_dismissed_stage is None

    entry = _latest_history_entry(db_session, application.id)
    assert entry.event_type == HistoryEventType.REINSTATED
    assert entry.old_stage == Stage.REJECTED
    assert entry.new_stage == original_stage
    assert entry.actor_id == recruiter.id


@pytest.mark.parametrize("current_stage", ACTIVE_STAGES + [Stage.HIRED])
def test_reinstate_from_non_rejected_fails(
    client, recruiter, make_opening, make_application, db_session, current_stage
):
    opening = make_opening()
    application = make_application(opening)
    _set_application_stage(db_session, application, current_stage)
    stage_changed_at_before = application.stage_changed_at

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(f"/applications/{application.id}/reinstate", headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"] == "Only a rejected application can be reinstated."

    db_session.refresh(application)
    assert application.current_stage == current_stage
    assert application.stage_changed_at == stage_changed_at_before


# ---- Interviewer is forbidden on every pipeline endpoint ---------------


def test_interviewer_forbidden_on_all_pipeline_endpoints(
    client, interviewer, make_opening, make_application, db_session
):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "interviewer@example.com")

    advance_response = client.post(
        f"/applications/{application.id}/advance",
        json={"to_stage": "screening"},
        headers=headers,
    )
    assert advance_response.status_code == 403

    reject_response = client.post(f"/applications/{application.id}/reject", headers=headers)
    assert reject_response.status_code == 403

    _set_application_stage(db_session, application, Stage.REJECTED, rejected_from_stage=Stage.APPLIED)
    reinstate_response = client.post(f"/applications/{application.id}/reinstate", headers=headers)
    assert reinstate_response.status_code == 403
