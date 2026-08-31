from app.models import ApplicationHistoryEntry, HistoryEventType, Stage
from tests.conftest import auth_headers


def test_recruiter_can_create_application_under_opening(client, recruiter, make_opening):
    opening = make_opening()
    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        f"/openings/{opening.id}/applications",
        json={
            "candidate_name": "Priya Patel",
            "candidate_email": "priya@example.com",
            "source": "referral",
            "notes": "Strong portfolio.",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["candidate_name"] == "Priya Patel"
    assert body["job_opening_id"] == opening.id
    assert body["current_stage"] == "applied"
    assert body["created_by_id"] == recruiter.id


def test_create_application_writes_created_history_entry(client, recruiter, make_opening, db_session):
    opening = make_opening()
    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        f"/openings/{opening.id}/applications",
        json={"candidate_name": "Priya Patel", "candidate_email": "priya@example.com"},
        headers=headers,
    )
    assert response.status_code == 201
    application_id = response.json()["id"]

    entries = (
        db_session.query(ApplicationHistoryEntry)
        .filter(ApplicationHistoryEntry.application_id == application_id)
        .all()
    )
    assert len(entries) == 1
    entry = entries[0]
    assert entry.event_type == HistoryEventType.CREATED
    assert entry.old_stage is None
    assert entry.new_stage == Stage.APPLIED
    assert entry.actor_id == recruiter.id


def test_create_application_rejects_blank_candidate_name(client, recruiter, make_opening):
    opening = make_opening()
    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        f"/openings/{opening.id}/applications",
        json={"candidate_name": "   ", "candidate_email": "priya@example.com"},
        headers=headers,
    )
    assert response.status_code == 422


def test_create_application_rejects_malformed_email(client, recruiter, make_opening):
    opening = make_opening()
    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        f"/openings/{opening.id}/applications",
        json={"candidate_name": "Priya Patel", "candidate_email": "not-an-email"},
        headers=headers,
    )
    assert response.status_code == 422


def test_create_application_404_for_missing_opening(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        "/openings/999999/applications",
        json={"candidate_name": "Priya Patel", "candidate_email": "priya@example.com"},
        headers=headers,
    )
    assert response.status_code == 404


def test_interviewer_cannot_create_application(client, interviewer, make_opening):
    opening = make_opening()
    headers = auth_headers(client, "interviewer@example.com")
    response = client.post(
        f"/openings/{opening.id}/applications",
        json={"candidate_name": "Priya Patel", "candidate_email": "priya@example.com"},
        headers=headers,
    )
    assert response.status_code == 403


def test_recruiter_can_list_applications_for_opening(client, recruiter, make_opening, make_application):
    opening = make_opening()
    other_opening = make_opening(title="Other Role")
    make_application(opening, candidate_name="In This Opening")
    make_application(other_opening, candidate_name="In A Different Opening")

    headers = auth_headers(client, "recruiter@example.com")
    response = client.get(f"/openings/{opening.id}/applications", headers=headers)
    assert response.status_code == 200
    names = {a["candidate_name"] for a in response.json()}
    assert names == {"In This Opening"}


def test_interviewer_cannot_list_applications_for_opening(client, interviewer, make_opening):
    opening = make_opening()
    headers = auth_headers(client, "interviewer@example.com")
    response = client.get(f"/openings/{opening.id}/applications", headers=headers)
    assert response.status_code == 403


def test_recruiter_can_edit_application(client, recruiter, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening, notes="Original notes.")
    headers = auth_headers(client, "recruiter@example.com")
    response = client.patch(
        f"/applications/{application.id}",
        json={"notes": "Updated after phone screen."},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["notes"] == "Updated after phone screen."
    # Untouched fields survive a partial update.
    assert body["candidate_name"] == "Jamie Candidate"


def test_interviewer_cannot_edit_application(client, interviewer, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "interviewer@example.com")
    response = client.patch(
        f"/applications/{application.id}",
        json={"notes": "Hijacked notes."},
        headers=headers,
    )
    assert response.status_code == 403


def test_get_missing_application_returns_404(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/applications/999999", headers=headers)
    assert response.status_code == 404
