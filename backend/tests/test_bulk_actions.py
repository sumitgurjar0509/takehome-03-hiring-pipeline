from datetime import datetime, timezone

from app.models import ApplicationHistoryEntry, HistoryEventType, Stage
from tests.conftest import auth_headers


def _touch(db_session, application, **fields):
    for key, value in fields.items():
        setattr(application, key, value)
    db_session.commit()
    db_session.refresh(application)


def _history_event_types(db_session, application_id):
    entries = (
        db_session.query(ApplicationHistoryEntry)
        .filter(ApplicationHistoryEntry.application_id == application_id)
        .all()
    )
    return [e.event_type for e in entries]


def test_bulk_advance_mixed_batch_returns_per_item_results(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    eligible = make_application(opening, candidate_name="Eligible")
    hired = make_application(opening, candidate_name="Already Hired")
    _touch(db_session, hired, current_stage=Stage.HIRED)
    rejected = make_application(opening, candidate_name="Already Rejected")
    _touch(db_session, rejected, current_stage=Stage.REJECTED, rejected_from_stage=Stage.INTERVIEW)

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        "/applications/bulk",
        json={"application_ids": [eligible.id, hired.id, rejected.id], "action": "advance"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    results_by_id = {r["application_id"]: r for r in response.json()["results"]}

    assert results_by_id[eligible.id]["success"] is True
    assert results_by_id[eligible.id]["message"] == "Advanced to Screening."

    assert results_by_id[hired.id]["success"] is False
    assert results_by_id[hired.id]["message"] == "Cannot advance: this application is already Hired, a final stage."

    assert results_by_id[rejected.id]["success"] is False
    assert results_by_id[rejected.id]["message"] == (
        "Cannot advance a rejected application — reinstate it before moving it forward."
    )

    # One ineligible item never blocked the eligible one from actually moving.
    db_session.refresh(eligible)
    db_session.refresh(hired)
    db_session.refresh(rejected)
    assert eligible.current_stage == Stage.SCREENING
    assert hired.current_stage == Stage.HIRED
    assert rejected.current_stage == Stage.REJECTED
    assert rejected.rejected_from_stage == Stage.INTERVIEW  # untouched by the failed attempt

    assert HistoryEventType.STAGE_CHANGE in _history_event_types(db_session, eligible.id)
    assert _history_event_types(db_session, hired.id) == []
    assert _history_event_types(db_session, rejected.id) == []


def test_bulk_reject_mixed_batch_returns_per_item_results(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    eligible = make_application(opening, candidate_name="Eligible")
    hired = make_application(opening, candidate_name="Already Hired")
    _touch(db_session, hired, current_stage=Stage.HIRED)
    already_rejected = make_application(opening, candidate_name="Already Rejected")
    _touch(
        db_session, already_rejected, current_stage=Stage.REJECTED, rejected_from_stage=Stage.OFFER
    )

    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        "/applications/bulk",
        json={
            "application_ids": [eligible.id, hired.id, already_rejected.id],
            "action": "reject",
        },
        headers=headers,
    )
    assert response.status_code == 200, response.text
    results_by_id = {r["application_id"]: r for r in response.json()["results"]}

    assert results_by_id[eligible.id]["success"] is True
    assert results_by_id[eligible.id]["message"] == "Rejected."

    assert results_by_id[hired.id]["success"] is False
    assert results_by_id[hired.id]["message"] == "A hired application cannot be rejected."

    assert results_by_id[already_rejected.id]["success"] is False
    assert results_by_id[already_rejected.id]["message"] == "This application is already rejected."

    db_session.refresh(eligible)
    db_session.refresh(hired)
    assert eligible.current_stage == Stage.REJECTED
    assert eligible.rejected_from_stage == Stage.APPLIED
    assert hired.current_stage == Stage.HIRED  # unaffected by the failed attempt


def test_bulk_action_reports_failure_for_nonexistent_application(
    client, recruiter, make_opening, make_application
):
    opening = make_opening()
    real = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.post(
        "/applications/bulk",
        json={"application_ids": [real.id, 999999], "action": "advance"},
        headers=headers,
    )
    assert response.status_code == 200
    results_by_id = {r["application_id"]: r for r in response.json()["results"]}
    assert results_by_id[real.id]["success"] is True
    assert results_by_id[999999]["success"] is False
    assert results_by_id[999999]["message"] == "Application not found."


def test_bulk_advance_clears_stall_dismissal_on_success(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    application = make_application(opening)
    _touch(
        db_session,
        application,
        stall_dismissed_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        stall_dismissed_stage=Stage.APPLIED,
    )
    headers = auth_headers(client, "recruiter@example.com")

    response = client.post(
        "/applications/bulk",
        json={"application_ids": [application.id], "action": "advance"},
        headers=headers,
    )
    assert response.status_code == 200
    db_session.refresh(application)
    assert application.stall_dismissed_at is None
    assert application.stall_dismissed_stage is None


def test_bulk_action_rejects_empty_application_ids(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        "/applications/bulk", json={"application_ids": [], "action": "advance"}, headers=headers
    )
    assert response.status_code == 422


def test_bulk_action_rejects_invalid_action_value(client, recruiter, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.post(
        "/applications/bulk",
        json={"application_ids": [application.id], "action": "delete"},
        headers=headers,
    )
    assert response.status_code == 422


def test_interviewer_forbidden_from_bulk_advance(client, interviewer, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "interviewer@example.com")

    response = client.post(
        "/applications/bulk",
        json={"application_ids": [application.id], "action": "advance"},
        headers=headers,
    )
    assert response.status_code == 403


def test_interviewer_forbidden_from_bulk_reject(client, interviewer, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "interviewer@example.com")

    response = client.post(
        "/applications/bulk",
        json={"application_ids": [application.id], "action": "reject"},
        headers=headers,
    )
    assert response.status_code == 403
