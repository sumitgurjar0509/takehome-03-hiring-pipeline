from tests.conftest import auth_headers


def test_recruiter_can_create_opening(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        "/openings",
        json={
            "title": "Backend Engineer",
            "department": "Engineering",
            "description": "Own the API.",
            "status": "open",
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "Backend Engineer"
    assert body["department"] == "Engineering"
    assert body["status"] == "open"
    assert body["archived"] is False
    assert body["created_by_id"] == recruiter.id


def test_create_opening_rejects_blank_title(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.post(
        "/openings",
        json={"title": "   ", "department": "Engineering"},
        headers=headers,
    )
    assert response.status_code == 422


def test_interviewer_cannot_create_opening(client, interviewer):
    headers = auth_headers(client, "interviewer@example.com")
    response = client.post(
        "/openings",
        json={"title": "Backend Engineer", "department": "Engineering"},
        headers=headers,
    )
    assert response.status_code == 403


def test_recruiter_can_edit_opening(client, recruiter, make_opening):
    opening = make_opening(title="Original Title")
    headers = auth_headers(client, "recruiter@example.com")
    response = client.patch(
        f"/openings/{opening.id}",
        json={"title": "Updated Title", "status": "closed"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "Updated Title"
    assert body["status"] == "closed"
    # Untouched fields survive a partial update.
    assert body["department"] == "Engineering"


def test_interviewer_cannot_edit_opening(client, interviewer, make_opening):
    opening = make_opening()
    headers = auth_headers(client, "interviewer@example.com")
    response = client.patch(
        f"/openings/{opening.id}",
        json={"title": "Hijacked Title"},
        headers=headers,
    )
    assert response.status_code == 403


def test_archive_hides_from_default_list_but_not_from_include_archived(
    client, recruiter, make_opening
):
    visible = make_opening(title="Stays Visible")
    to_archive = make_opening(title="Gets Archived")
    headers = auth_headers(client, "recruiter@example.com")

    archive_response = client.post(f"/openings/{to_archive.id}/archive", headers=headers)
    assert archive_response.status_code == 200
    assert archive_response.json()["archived"] is True

    default_list = client.get("/openings", headers=headers)
    assert default_list.status_code == 200
    default_titles = {o["title"] for o in default_list.json()}
    assert visible.title in default_titles
    assert to_archive.title not in default_titles

    with_archived = client.get("/openings", params={"include_archived": True}, headers=headers)
    assert with_archived.status_code == 200
    all_titles = {o["title"] for o in with_archived.json()}
    assert visible.title in all_titles
    assert to_archive.title in all_titles

    # Archiving never touches the opening's own applications — it's still
    # fetchable directly by id, just hidden from the default list view.
    direct_fetch = client.get(f"/openings/{to_archive.id}", headers=headers)
    assert direct_fetch.status_code == 200
    assert direct_fetch.json()["archived"] is True


def test_restore_brings_opening_back_to_default_list(client, recruiter, make_opening):
    opening = make_opening(archived=True)
    headers = auth_headers(client, "recruiter@example.com")

    restore_response = client.post(f"/openings/{opening.id}/restore", headers=headers)
    assert restore_response.status_code == 200
    assert restore_response.json()["archived"] is False

    default_list = client.get("/openings", headers=headers)
    titles = {o["title"] for o in default_list.json()}
    assert opening.title in titles


def test_interviewer_cannot_archive_opening(client, interviewer, make_opening):
    opening = make_opening()
    headers = auth_headers(client, "interviewer@example.com")
    response = client.post(f"/openings/{opening.id}/archive", headers=headers)
    assert response.status_code == 403


def test_interviewer_cannot_restore_opening(client, interviewer, make_opening):
    opening = make_opening(archived=True)
    headers = auth_headers(client, "interviewer@example.com")
    response = client.post(f"/openings/{opening.id}/restore", headers=headers)
    assert response.status_code == 403


def test_interviewer_can_list_and_view_openings(client, interviewer, make_opening):
    opening = make_opening()
    headers = auth_headers(client, "interviewer@example.com")

    list_response = client.get("/openings", headers=headers)
    assert list_response.status_code == 200

    detail_response = client.get(f"/openings/{opening.id}", headers=headers)
    assert detail_response.status_code == 200
    assert detail_response.json()["id"] == opening.id


def test_get_missing_opening_returns_404(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/openings/999999", headers=headers)
    assert response.status_code == 404
