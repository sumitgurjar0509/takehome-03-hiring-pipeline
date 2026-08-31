from app.models import ApplicationInterviewer, UserRole
from tests.conftest import auth_headers


def test_recruiter_can_assign_interviewer(client, recruiter, interviewer, make_opening, make_application, db_session):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.post(
        f"/applications/{application.id}/interviewers",
        json={"interviewer_id": interviewer.id},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert [i["id"] for i in body] == [interviewer.id]

    row = (
        db_session.query(ApplicationInterviewer)
        .filter(
            ApplicationInterviewer.application_id == application.id,
            ApplicationInterviewer.interviewer_id == interviewer.id,
        )
        .first()
    )
    assert row is not None


def test_assigning_a_recruiter_is_rejected(client, recruiter, make_opening, make_application, make_user, db_session):
    other_recruiter = make_user(email="other-recruiter@example.com")
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.post(
        f"/applications/{application.id}/interviewers",
        json={"interviewer_id": other_recruiter.id},
        headers=headers,
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Only users with the interviewer role can be assigned to a panel."

    row = (
        db_session.query(ApplicationInterviewer)
        .filter(ApplicationInterviewer.application_id == application.id)
        .first()
    )
    assert row is None


def test_assigning_a_nonexistent_user_returns_404(client, recruiter, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.post(
        f"/applications/{application.id}/interviewers",
        json={"interviewer_id": 999999},
        headers=headers,
    )
    assert response.status_code == 404


def test_assigning_the_same_interviewer_twice_is_idempotent(
    client, recruiter, interviewer, make_opening, make_application, db_session
):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    for _ in range(2):
        response = client.post(
            f"/applications/{application.id}/interviewers",
            json={"interviewer_id": interviewer.id},
            headers=headers,
        )
        assert response.status_code == 200

    rows = (
        db_session.query(ApplicationInterviewer)
        .filter(
            ApplicationInterviewer.application_id == application.id,
            ApplicationInterviewer.interviewer_id == interviewer.id,
        )
        .all()
    )
    assert len(rows) == 1


def test_recruiter_can_unassign_interviewer(
    client, recruiter, interviewer, make_opening, make_application, db_session
):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")
    client.post(
        f"/applications/{application.id}/interviewers",
        json={"interviewer_id": interviewer.id},
        headers=headers,
    )

    response = client.delete(f"/applications/{application.id}/interviewers/{interviewer.id}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == []

    row = (
        db_session.query(ApplicationInterviewer)
        .filter(ApplicationInterviewer.application_id == application.id)
        .first()
    )
    assert row is None


def test_unassign_when_not_assigned_returns_404(client, recruiter, interviewer, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.delete(f"/applications/{application.id}/interviewers/{interviewer.id}", headers=headers)
    assert response.status_code == 404


def test_multiple_interviewers_can_be_assigned_to_one_application(
    client, recruiter, make_opening, make_application, make_user
):
    first = make_user(email="first-interviewer@example.com", role=UserRole.INTERVIEWER)
    second = make_user(email="second-interviewer@example.com", role=UserRole.INTERVIEWER)
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    client.post(f"/applications/{application.id}/interviewers", json={"interviewer_id": first.id}, headers=headers)
    response = client.post(
        f"/applications/{application.id}/interviewers", json={"interviewer_id": second.id}, headers=headers
    )
    assert response.status_code == 200
    assert {i["id"] for i in response.json()} == {first.id, second.id}


def test_one_interviewer_can_be_assigned_across_multiple_openings(
    client, recruiter, interviewer, make_opening, make_application
):
    opening_a = make_opening(title="Opening A")
    opening_b = make_opening(title="Opening B")
    application_a = make_application(opening_a, candidate_name="Candidate A")
    application_b = make_application(opening_b, candidate_name="Candidate B")
    headers = auth_headers(client, "recruiter@example.com")

    response_a = client.post(
        f"/applications/{application_a.id}/interviewers", json={"interviewer_id": interviewer.id}, headers=headers
    )
    response_b = client.post(
        f"/applications/{application_b.id}/interviewers", json={"interviewer_id": interviewer.id}, headers=headers
    )
    assert response_a.status_code == 200
    assert response_b.status_code == 200


def test_interviewer_forbidden_from_assign_unassign_and_panel_list(
    client, interviewer, make_opening, make_application
):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "interviewer@example.com")

    assign_response = client.post(
        f"/applications/{application.id}/interviewers",
        json={"interviewer_id": interviewer.id},
        headers=headers,
    )
    assert assign_response.status_code == 403

    unassign_response = client.delete(
        f"/applications/{application.id}/interviewers/{interviewer.id}", headers=headers
    )
    assert unassign_response.status_code == 403

    list_panel_response = client.get(f"/applications/{application.id}/interviewers", headers=headers)
    assert list_panel_response.status_code == 403

    list_interviewers_response = client.get("/interviewers", headers=headers)
    assert list_interviewers_response.status_code == 403


def test_my_assignments_only_shows_own_applications(
    client, recruiter, make_opening, make_application, make_user
):
    interviewer_a = make_user(email="panel-a@example.com", role=UserRole.INTERVIEWER)
    interviewer_b = make_user(email="panel-b@example.com", role=UserRole.INTERVIEWER)
    opening = make_opening()
    application_a = make_application(opening, candidate_name="Assigned To A")
    application_b = make_application(opening, candidate_name="Assigned To B")
    headers = auth_headers(client, "recruiter@example.com")

    client.post(
        f"/applications/{application_a.id}/interviewers",
        json={"interviewer_id": interviewer_a.id},
        headers=headers,
    )
    client.post(
        f"/applications/{application_b.id}/interviewers",
        json={"interviewer_id": interviewer_b.id},
        headers=headers,
    )

    headers_a = auth_headers(client, "panel-a@example.com")
    response_a = client.get("/my-assignments", headers=headers_a)
    assert response_a.status_code == 200
    names_a = {a["candidate_name"] for a in response_a.json()}
    assert names_a == {"Assigned To A"}
    assert response_a.json()[0]["job_opening_title"] == opening.title


def test_my_assignments_requires_interviewer_role(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/my-assignments", headers=headers)
    assert response.status_code == 403


def test_interviewer_can_fetch_an_assigned_application(
    client, recruiter, interviewer, make_opening, make_application
):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")
    client.post(
        f"/applications/{application.id}/interviewers",
        json={"interviewer_id": interviewer.id},
        headers=headers,
    )

    interviewer_headers = auth_headers(client, "interviewer@example.com")
    response = client.get(f"/applications/{application.id}", headers=interviewer_headers)
    assert response.status_code == 200
    assert response.json()["id"] == application.id


def test_interviewer_cannot_fetch_an_unassigned_application(
    client, interviewer, make_opening, make_application
):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "interviewer@example.com")

    response = client.get(f"/applications/{application.id}", headers=headers)
    assert response.status_code == 404


def test_recruiter_can_still_fetch_any_application(client, recruiter, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get(f"/applications/{application.id}", headers=headers)
    assert response.status_code == 200
