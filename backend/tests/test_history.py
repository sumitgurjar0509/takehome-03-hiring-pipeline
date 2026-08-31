from app.models import HistoryEventType, Stage
from tests.conftest import auth_headers


def _assign(client, headers, application_id, interviewer_id):
    response = client.post(
        f"/applications/{application_id}/interviewers",
        json={"interviewer_id": interviewer_id},
        headers=headers,
    )
    assert response.status_code == 200, response.text


def test_feedback_write_succeeds_for_assigned_interviewer(
    client, recruiter, interviewer, make_opening, make_application, db_session
):
    opening = make_opening()
    application = make_application(opening)
    recruiter_headers = auth_headers(client, "recruiter@example.com")
    _assign(client, recruiter_headers, application.id, interviewer.id)

    interviewer_headers = auth_headers(client, "interviewer@example.com")
    response = client.post(
        f"/applications/{application.id}/feedback",
        json={"feedback_text": "Strong on system design, weak on communication."},
        headers=interviewer_headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["event_type"] == "feedback"
    assert body["feedback_text"] == "Strong on system design, weak on communication."
    assert body["old_stage"] is None
    assert body["new_stage"] is None
    assert body["actor_id"] == interviewer.id
    assert body["actor_name"] == interviewer.name


def test_feedback_forbidden_for_unassigned_interviewer(
    client, interviewer, make_opening, make_application
):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "interviewer@example.com")

    response = client.post(
        f"/applications/{application.id}/feedback",
        json={"feedback_text": "Should not be allowed."},
        headers=headers,
    )
    assert response.status_code == 403


def test_feedback_forbidden_for_recruiter(client, recruiter, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.post(
        f"/applications/{application.id}/feedback",
        json={"feedback_text": "Recruiters don't leave feedback."},
        headers=headers,
    )
    assert response.status_code == 403


def test_feedback_rejects_blank_text(
    client, recruiter, interviewer, make_opening, make_application
):
    opening = make_opening()
    application = make_application(opening)
    recruiter_headers = auth_headers(client, "recruiter@example.com")
    _assign(client, recruiter_headers, application.id, interviewer.id)

    interviewer_headers = auth_headers(client, "interviewer@example.com")
    response = client.post(
        f"/applications/{application.id}/feedback",
        json={"feedback_text": "   "},
        headers=interviewer_headers,
    )
    assert response.status_code == 422


def test_feedback_on_nonexistent_application_is_forbidden_not_not_found(client, interviewer):
    headers = auth_headers(client, "interviewer@example.com")
    response = client.post(
        "/applications/999999/feedback",
        json={"feedback_text": "Doesn't matter."},
        headers=headers,
    )
    assert response.status_code == 403


def test_history_returns_events_in_order_with_actor_names(
    client, recruiter, interviewer, make_opening, db_session
):
    opening = make_opening()
    recruiter_headers = auth_headers(client, "recruiter@example.com")

    create_response = client.post(
        f"/openings/{opening.id}/applications",
        json={"candidate_name": "Timeline Candidate", "candidate_email": "timeline@example.com"},
        headers=recruiter_headers,
    )
    assert create_response.status_code == 201
    application_id = create_response.json()["id"]

    advance_response = client.post(
        f"/applications/{application_id}/advance",
        json={"to_stage": "screening"},
        headers=recruiter_headers,
    )
    assert advance_response.status_code == 200

    _assign(client, recruiter_headers, application_id, interviewer.id)
    interviewer_headers = auth_headers(client, "interviewer@example.com")
    feedback_response = client.post(
        f"/applications/{application_id}/feedback",
        json={"feedback_text": "Solid candidate."},
        headers=interviewer_headers,
    )
    assert feedback_response.status_code == 201

    reject_response = client.post(f"/applications/{application_id}/reject", headers=recruiter_headers)
    assert reject_response.status_code == 200

    reinstate_response = client.post(
        f"/applications/{application_id}/reinstate", headers=recruiter_headers
    )
    assert reinstate_response.status_code == 200

    history_response = client.get(f"/applications/{application_id}/history", headers=recruiter_headers)
    assert history_response.status_code == 200
    entries = history_response.json()

    event_types = [e["event_type"] for e in entries]
    assert event_types == ["created", "stage_change", "feedback", "rejected", "reinstated"]

    created_ats = [e["created_at"] for e in entries]
    assert created_ats == sorted(created_ats)

    created_entry, stage_change_entry, feedback_entry, rejected_entry, reinstated_entry = entries

    assert created_entry["old_stage"] is None
    assert created_entry["new_stage"] == "applied"
    assert created_entry["actor_name"] == recruiter.name

    assert stage_change_entry["old_stage"] == "applied"
    assert stage_change_entry["new_stage"] == "screening"
    assert stage_change_entry["actor_name"] == recruiter.name

    assert feedback_entry["feedback_text"] == "Solid candidate."
    assert feedback_entry["actor_name"] == interviewer.name
    assert feedback_entry["old_stage"] is None
    assert feedback_entry["new_stage"] is None

    assert rejected_entry["old_stage"] == "screening"
    assert rejected_entry["new_stage"] == "rejected"
    assert rejected_entry["actor_name"] == recruiter.name

    assert reinstated_entry["old_stage"] == "rejected"
    assert reinstated_entry["new_stage"] == "screening"
    assert reinstated_entry["actor_name"] == recruiter.name


def test_history_accessible_to_recruiter(client, recruiter, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get(f"/applications/{application.id}/history", headers=headers)
    assert response.status_code == 200


def test_history_accessible_to_assigned_interviewer(
    client, recruiter, interviewer, make_opening, make_application
):
    opening = make_opening()
    application = make_application(opening)
    recruiter_headers = auth_headers(client, "recruiter@example.com")
    _assign(client, recruiter_headers, application.id, interviewer.id)

    interviewer_headers = auth_headers(client, "interviewer@example.com")
    response = client.get(f"/applications/{application.id}/history", headers=interviewer_headers)
    assert response.status_code == 200


def test_history_not_found_for_unassigned_interviewer(
    client, interviewer, make_opening, make_application
):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "interviewer@example.com")

    response = client.get(f"/applications/{application.id}/history", headers=headers)
    assert response.status_code == 404
