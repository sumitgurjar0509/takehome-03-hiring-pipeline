from datetime import datetime, timedelta, timezone

from app.models import ApplicationHistoryEntry, HistoryEventType, OpeningStatus, Stage
from app.services.dashboard import _month_start, _week_start
from tests.conftest import auth_headers


def _touch(db_session, application, **fields):
    for key, value in fields.items():
        setattr(application, key, value)
    db_session.commit()
    db_session.refresh(application)


def _history_entry(db_session, application, actor, event_type, new_stage, created_at, old_stage=None):
    entry = ApplicationHistoryEntry(
        application_id=application.id,
        event_type=event_type,
        old_stage=old_stage,
        new_stage=new_stage,
        actor_id=actor.id,
        created_at=created_at,
    )
    db_session.add(entry)
    db_session.commit()
    return entry


def test_open_positions_counts_only_open_status(client, recruiter, make_opening):
    make_opening(title="Open A", status=OpeningStatus.OPEN)
    make_opening(title="Open B", status=OpeningStatus.OPEN)
    make_opening(title="Closed C", status=OpeningStatus.CLOSED)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json()["open_positions"] == 2


def test_active_applications_excludes_terminal_stages(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    make_application(opening, candidate_name="Applied One")
    screening = make_application(opening, candidate_name="Screening One")
    _touch(db_session, screening, current_stage=Stage.SCREENING)
    hired = make_application(opening, candidate_name="Hired One")
    _touch(db_session, hired, current_stage=Stage.HIRED)
    rejected = make_application(opening, candidate_name="Rejected One")
    _touch(db_session, rejected, current_stage=Stage.REJECTED, rejected_from_stage=Stage.OFFER)

    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json()["active_applications"] == 2


def test_interviews_scheduled_this_week_counts_only_stage_change_into_interview_this_week(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    now = datetime.now(timezone.utc)
    this_week_start = _week_start(now)
    last_week_moment = this_week_start - timedelta(days=1)

    counted = make_application(opening, candidate_name="Counted")
    _history_entry(
        db_session, counted, recruiter, HistoryEventType.STAGE_CHANGE, Stage.INTERVIEW,
        created_at=this_week_start + timedelta(hours=1),
    )

    last_week = make_application(opening, candidate_name="Last Week")
    _history_entry(
        db_session, last_week, recruiter, HistoryEventType.STAGE_CHANGE, Stage.INTERVIEW,
        created_at=last_week_moment,
    )

    wrong_stage = make_application(opening, candidate_name="Wrong Stage")
    _history_entry(
        db_session, wrong_stage, recruiter, HistoryEventType.STAGE_CHANGE, Stage.OFFER,
        created_at=this_week_start + timedelta(hours=2),
    )

    reinstated = make_application(opening, candidate_name="Reinstated")
    _history_entry(
        db_session, reinstated, recruiter, HistoryEventType.REINSTATED, Stage.INTERVIEW,
        created_at=this_week_start + timedelta(hours=3), old_stage=Stage.REJECTED,
    )

    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json()["interviews_scheduled_this_week"] == 1


def test_hires_this_month_counts_only_stage_change_into_hired_this_month(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    now = datetime.now(timezone.utc)
    this_month_start = _month_start(now)
    last_month_moment = this_month_start - timedelta(days=1)

    counted = make_application(opening, candidate_name="Counted")
    _history_entry(
        db_session, counted, recruiter, HistoryEventType.STAGE_CHANGE, Stage.HIRED,
        created_at=this_month_start + timedelta(hours=1),
    )

    last_month = make_application(opening, candidate_name="Last Month")
    _history_entry(
        db_session, last_month, recruiter, HistoryEventType.STAGE_CHANGE, Stage.HIRED,
        created_at=last_month_moment,
    )

    wrong_event_type = make_application(opening, candidate_name="Wrong Event Type")
    _history_entry(
        db_session, wrong_event_type, recruiter, HistoryEventType.REJECTED, Stage.HIRED,
        created_at=this_month_start + timedelta(hours=2), old_stage=Stage.OFFER,
    )

    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    assert response.json()["hires_this_month"] == 1


def test_by_opening_breakdown(client, recruiter, make_opening, make_application):
    opening_a = make_opening(title="Opening A")
    opening_b = make_opening(title="Opening B")
    make_application(opening_a, candidate_name="A1")
    make_application(opening_a, candidate_name="A2")
    make_application(opening_b, candidate_name="B1")

    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    by_opening = {row["job_opening_title"]: row["count"] for row in response.json()["by_opening"]}
    assert by_opening["Opening A"] == 2
    assert by_opening["Opening B"] == 1


def test_by_stage_breakdown_includes_all_stages_with_zero_counts(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    make_application(opening, candidate_name="Applied One")
    screening = make_application(opening, candidate_name="Screening One")
    _touch(db_session, screening, current_stage=Stage.SCREENING)

    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    by_stage = {row["stage"]: row["count"] for row in response.json()["by_stage"]}
    assert set(by_stage.keys()) == {s.value for s in Stage}
    assert by_stage["applied"] == 1
    assert by_stage["screening"] == 1
    assert by_stage["interview"] == 0
    assert by_stage["offer"] == 0
    assert by_stage["hired"] == 0
    assert by_stage["rejected"] == 0


def test_applications_per_week_has_13_zero_filled_buckets_in_order(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    now = datetime.now(timezone.utc)
    this_week_start = _week_start(now)
    thirteen_weeks_start = this_week_start - timedelta(weeks=12)

    oldest_bucket_app = make_application(opening, candidate_name="Oldest Bucket")
    _touch(db_session, oldest_bucket_app, created_at=thirteen_weeks_start + timedelta(hours=1))

    current_bucket_app_1 = make_application(opening, candidate_name="Current Bucket 1")
    _touch(db_session, current_bucket_app_1, created_at=this_week_start + timedelta(hours=1))
    current_bucket_app_2 = make_application(opening, candidate_name="Current Bucket 2")
    _touch(db_session, current_bucket_app_2, created_at=this_week_start + timedelta(hours=2))

    too_old_app = make_application(opening, candidate_name="Too Old")
    _touch(db_session, too_old_app, created_at=thirteen_weeks_start - timedelta(days=1))

    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 200
    weeks = response.json()["applications_per_week"]

    assert len(weeks) == 13
    assert weeks[0]["week_start"] == thirteen_weeks_start.date().isoformat()
    assert weeks[0]["count"] == 1
    assert weeks[-1]["week_start"] == this_week_start.date().isoformat()
    assert weeks[-1]["count"] == 2
    # everything strictly between the two touched buckets is zero-filled
    assert all(w["count"] == 0 for w in weeks[1:-1])
    # ascending chronological order
    assert [w["week_start"] for w in weeks] == sorted(w["week_start"] for w in weeks)


def test_interviewer_forbidden_from_dashboard(client, interviewer):
    headers = auth_headers(client, "interviewer@example.com")
    response = client.get("/dashboard", headers=headers)
    assert response.status_code == 403
