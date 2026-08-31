from datetime import datetime, timedelta, timezone

from app.models import Stage
from tests.conftest import auth_headers

def _eleven_days_ago() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=11)


def _five_days_ago() -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=5)


def _touch(db_session, application, **fields):
    for key, value in fields.items():
        setattr(application, key, value)
    db_session.commit()
    db_session.refresh(application)


def _alert_ids(client, headers) -> set[int]:
    response = client.get("/alerts", headers=headers)
    assert response.status_code == 200
    return {row["id"] for row in response.json()}


def test_application_stalled_more_than_ten_days_appears(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    application = make_application(opening)
    _touch(db_session, application, stage_changed_at=_eleven_days_ago())
    headers = auth_headers(client, "recruiter@example.com")

    assert application.id in _alert_ids(client, headers)


def test_application_stalled_less_than_ten_days_does_not_appear(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    application = make_application(opening)
    _touch(db_session, application, stage_changed_at=_five_days_ago())
    headers = auth_headers(client, "recruiter@example.com")

    assert application.id not in _alert_ids(client, headers)


def test_application_just_under_ten_days_does_not_appear(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    application = make_application(opening)
    # A few minutes' margin under the threshold — an exact 10-day instant
    # isn't reliably testable, since real time passes between setting this
    # fixture and the query running, which would push it just past 10 days
    # by query time and make the test flaky rather than wrong.
    _touch(
        db_session,
        application,
        stage_changed_at=datetime.now(timezone.utc) - timedelta(days=10) + timedelta(minutes=5),
    )
    headers = auth_headers(client, "recruiter@example.com")

    # "more than ten days" is strict — just under ten is not yet stalled.
    assert application.id not in _alert_ids(client, headers)


def test_hired_and_rejected_never_appear_even_if_old(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    hired = make_application(opening, candidate_name="Hired One")
    _touch(db_session, hired, stage_changed_at=_eleven_days_ago(), current_stage=Stage.HIRED)
    rejected = make_application(opening, candidate_name="Rejected One")
    _touch(
        db_session,
        rejected,
        stage_changed_at=_eleven_days_ago(),
        current_stage=Stage.REJECTED,
        rejected_from_stage=Stage.OFFER,
    )
    headers = auth_headers(client, "recruiter@example.com")

    ids = _alert_ids(client, headers)
    assert hired.id not in ids
    assert rejected.id not in ids


def test_dismiss_removes_from_list(client, recruiter, make_opening, make_application, db_session):
    opening = make_opening()
    application = make_application(opening)
    _touch(db_session, application, stage_changed_at=_eleven_days_ago())
    headers = auth_headers(client, "recruiter@example.com")
    assert application.id in _alert_ids(client, headers)

    dismiss_response = client.post(f"/applications/{application.id}/dismiss-alert", headers=headers)
    assert dismiss_response.status_code == 200

    db_session.refresh(application)
    assert application.stall_dismissed_at is not None
    assert application.stall_dismissed_stage == Stage.APPLIED
    assert application.id not in _alert_ids(client, headers)


def test_dismissed_application_stalling_again_in_same_stage_does_not_reappear(
    client, recruiter, make_opening, make_application, db_session
):
    """The application never transitions — the dismissal stays valid forever
    in that same stage, no matter how much later it's checked."""
    opening = make_opening()
    application = make_application(opening)
    _touch(db_session, application, stage_changed_at=_eleven_days_ago())
    headers = auth_headers(client, "recruiter@example.com")

    client.post(f"/applications/{application.id}/dismiss-alert", headers=headers)
    assert application.id not in _alert_ids(client, headers)

    # Time passes further; still in Applied, never transitioned.
    _touch(db_session, application, stage_changed_at=datetime.now(timezone.utc) - timedelta(days=30))
    assert application.id not in _alert_ids(client, headers)


def test_dismissed_application_that_advances_and_restalls_in_new_stage_reappears(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    application = make_application(opening)
    _touch(db_session, application, stage_changed_at=_eleven_days_ago())
    headers = auth_headers(client, "recruiter@example.com")

    client.post(f"/applications/{application.id}/dismiss-alert", headers=headers)
    assert application.id not in _alert_ids(client, headers)

    advance_response = client.post(
        f"/applications/{application.id}/advance",
        json={"to_stage": "screening"},
        headers=headers,
    )
    assert advance_response.status_code == 200

    db_session.refresh(application)
    assert application.stall_dismissed_at is None
    assert application.stall_dismissed_stage is None
    assert application.current_stage == Stage.SCREENING

    # Freshly advanced, not stalled yet.
    assert application.id not in _alert_ids(client, headers)

    # It now stalls again, in the NEW stage.
    _touch(db_session, application, stage_changed_at=_eleven_days_ago())
    assert application.id in _alert_ids(client, headers)


def test_rejected_then_reinstated_application_reappears_in_reinstated_stage_despite_stale_dismissal(
    client, recruiter, make_opening, make_application, db_session
):
    """
    The one most likely to be silently wrong: dismiss while stalled in
    Interview, get rejected, get reinstated back to that SAME stage
    (Interview). Because reject and reinstate both clear the dismissal
    columns (goal 4), the old "Interview" dismissal from before the
    rejection must NOT suppress a genuinely new stall period in Interview
    after reinstatement, even though stall_dismissed_stage would still
    equal current_stage if it had survived.
    """
    opening = make_opening()
    application = make_application(opening)
    _touch(
        db_session,
        application,
        current_stage=Stage.INTERVIEW,
        stage_changed_at=_eleven_days_ago(),
    )
    headers = auth_headers(client, "recruiter@example.com")

    assert application.id in _alert_ids(client, headers)
    dismiss_response = client.post(f"/applications/{application.id}/dismiss-alert", headers=headers)
    assert dismiss_response.status_code == 200
    db_session.refresh(application)
    assert application.stall_dismissed_stage == Stage.INTERVIEW
    assert application.id not in _alert_ids(client, headers)

    reject_response = client.post(f"/applications/{application.id}/reject", headers=headers)
    assert reject_response.status_code == 200
    db_session.refresh(application)
    assert application.current_stage == Stage.REJECTED
    assert application.rejected_from_stage == Stage.INTERVIEW
    assert application.stall_dismissed_at is None
    assert application.stall_dismissed_stage is None

    reinstate_response = client.post(f"/applications/{application.id}/reinstate", headers=headers)
    assert reinstate_response.status_code == 200
    db_session.refresh(application)
    assert application.current_stage == Stage.INTERVIEW  # back to the exact same stage
    assert application.stall_dismissed_at is None
    assert application.stall_dismissed_stage is None

    # Not stalled yet — reinstate just reset stage_changed_at to now.
    assert application.id not in _alert_ids(client, headers)

    # It now stalls again in Interview for a second, genuinely new period.
    _touch(db_session, application, stage_changed_at=_eleven_days_ago())
    assert application.id in _alert_ids(client, headers)


def test_interviewer_forbidden_from_alerts_list(client, interviewer):
    headers = auth_headers(client, "interviewer@example.com")
    response = client.get("/alerts", headers=headers)
    assert response.status_code == 403


def test_interviewer_forbidden_from_dismissing_alert(
    client, interviewer, make_opening, make_application
):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "interviewer@example.com")

    response = client.post(f"/applications/{application.id}/dismiss-alert", headers=headers)
    assert response.status_code == 403
