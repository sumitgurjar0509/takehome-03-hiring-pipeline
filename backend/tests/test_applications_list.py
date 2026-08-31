from datetime import datetime, timedelta, timezone

from app.models import Stage
from tests.conftest import auth_headers


def _touch(db_session, application, **fields):
    for key, value in fields.items():
        setattr(application, key, value)
    db_session.commit()
    db_session.refresh(application)


def test_search_matches_candidate_name(client, recruiter, make_opening, make_application):
    opening = make_opening()
    make_application(opening, candidate_name="Priya Patel", candidate_email="priya@example.com")
    make_application(opening, candidate_name="Jordan Lee", candidate_email="jordan@example.com")
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications", params={"search": "priya"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert [a["candidate_name"] for a in body["results"]] == ["Priya Patel"]


def test_search_matches_candidate_email(client, recruiter, make_opening, make_application):
    opening = make_opening()
    make_application(opening, candidate_name="Priya Patel", candidate_email="priya@example.com")
    make_application(opening, candidate_name="Jordan Lee", candidate_email="jordan@example.com")
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications", params={"search": "jordan@example"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["candidate_email"] == "jordan@example.com"


def test_search_is_case_insensitive_and_partial(client, recruiter, make_opening, make_application):
    opening = make_opening()
    make_application(opening, candidate_name="Priya Patel", candidate_email="priya@example.com")
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications", params={"search": "PAT"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_search_with_no_matches_returns_empty(client, recruiter, make_opening, make_application):
    opening = make_opening()
    make_application(opening, candidate_name="Priya Patel", candidate_email="priya@example.com")
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications", params={"search": "nobody-matches-this"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 0
    assert body["results"] == []


def test_filter_by_job_opening_id(client, recruiter, make_opening, make_application):
    opening_a = make_opening(title="Opening A")
    opening_b = make_opening(title="Opening B")
    make_application(opening_a, candidate_name="In A")
    make_application(opening_b, candidate_name="In B")
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications", params={"job_opening_id": opening_a.id}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["candidate_name"] == "In A"


def test_filter_by_stage(client, recruiter, make_opening, make_application, db_session):
    opening = make_opening()
    make_application(opening, candidate_name="Applied Stage")
    screening = make_application(opening, candidate_name="Screening Stage")
    _touch(db_session, screening, current_stage=Stage.SCREENING)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications", params={"stage": "screening"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["candidate_name"] == "Screening Stage"


def test_filter_by_source_is_case_insensitive_exact_match(client, recruiter, make_opening, make_application):
    opening = make_opening()
    make_application(opening, candidate_name="Referral Candidate", source="referral")
    make_application(opening, candidate_name="LinkedIn Candidate", source="LinkedIn")
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications", params={"source": "REFERRAL"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["candidate_name"] == "Referral Candidate"


def test_filters_combine(client, recruiter, make_opening, make_application, db_session):
    opening_a = make_opening(title="Opening A")
    opening_b = make_opening(title="Opening B")
    match = make_application(opening_a, candidate_name="Match Candidate", source="referral")
    _touch(db_session, match, current_stage=Stage.SCREENING)
    make_application(opening_a, candidate_name="Wrong Stage", source="referral")
    make_application(opening_b, candidate_name="Wrong Opening", source="referral")
    wrong_source = make_application(opening_a, candidate_name="Wrong Source", source="LinkedIn")
    _touch(db_session, wrong_source, current_stage=Stage.SCREENING)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get(
        "/applications",
        params={"job_opening_id": opening_a.id, "stage": "screening", "source": "referral"},
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["results"][0]["candidate_name"] == "Match Candidate"


def test_sort_by_applied_date(client, recruiter, make_opening, make_application):
    opening = make_opening()
    make_application(opening, candidate_name="First Applied")
    make_application(opening, candidate_name="Second Applied")
    headers = auth_headers(client, "recruiter@example.com")

    asc = client.get("/applications", params={"sort": "applied_date"}, headers=headers)
    assert [a["candidate_name"] for a in asc.json()["results"]] == ["First Applied", "Second Applied"]

    desc = client.get("/applications", params={"sort": "-applied_date"}, headers=headers)
    assert [a["candidate_name"] for a in desc.json()["results"]] == ["Second Applied", "First Applied"]


def test_sort_by_last_update(client, recruiter, make_opening, make_application, db_session):
    opening = make_opening()
    earlier = make_application(opening, candidate_name="Updated Earlier")
    later = make_application(opening, candidate_name="Updated Later")
    now = datetime.now(timezone.utc)
    _touch(db_session, earlier, updated_at=now - timedelta(hours=2))
    _touch(db_session, later, updated_at=now - timedelta(hours=1))
    headers = auth_headers(client, "recruiter@example.com")

    asc = client.get("/applications", params={"sort": "last_update"}, headers=headers)
    assert [x["candidate_name"] for x in asc.json()["results"]] == ["Updated Earlier", "Updated Later"]

    desc = client.get("/applications", params={"sort": "-last_update"}, headers=headers)
    assert [x["candidate_name"] for x in desc.json()["results"]] == ["Updated Later", "Updated Earlier"]


def test_sort_by_stage_is_pipeline_order_not_alphabetical(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    offer = make_application(opening, candidate_name="At Offer")
    _touch(db_session, offer, current_stage=Stage.OFFER)
    make_application(opening, candidate_name="At Applied")
    interview = make_application(opening, candidate_name="At Interview")
    _touch(db_session, interview, current_stage=Stage.INTERVIEW)
    headers = auth_headers(client, "recruiter@example.com")

    asc = client.get("/applications", params={"sort": "stage"}, headers=headers)
    assert [x["candidate_name"] for x in asc.json()["results"]] == [
        "At Applied",
        "At Interview",
        "At Offer",
    ]

    desc = client.get("/applications", params={"sort": "-stage"}, headers=headers)
    assert [x["candidate_name"] for x in desc.json()["results"]] == [
        "At Offer",
        "At Interview",
        "At Applied",
    ]


def test_pagination_page_and_page_size(client, recruiter, make_opening, make_application):
    opening = make_opening()
    for i in range(5):
        make_application(opening, candidate_name=f"Candidate {i}", candidate_email=f"c{i}@example.com")
    headers = auth_headers(client, "recruiter@example.com")

    page1 = client.get(
        "/applications", params={"page": 1, "page_size": 2, "sort": "applied_date"}, headers=headers
    )
    page2 = client.get(
        "/applications", params={"page": 2, "page_size": 2, "sort": "applied_date"}, headers=headers
    )
    page3 = client.get(
        "/applications", params={"page": 3, "page_size": 2, "sort": "applied_date"}, headers=headers
    )

    assert page1.json()["total"] == 5
    assert page2.json()["total"] == 5
    assert len(page1.json()["results"]) == 2
    assert len(page2.json()["results"]) == 2
    assert len(page3.json()["results"]) == 1
    assert page1.json()["page"] == 1
    assert page1.json()["page_size"] == 2

    all_names = (
        [a["candidate_name"] for a in page1.json()["results"]]
        + [a["candidate_name"] for a in page2.json()["results"]]
        + [a["candidate_name"] for a in page3.json()["results"]]
    )
    assert all_names == [f"Candidate {i}" for i in range(5)]
    assert len(set(all_names)) == 5  # no duplicates or gaps across pages


def test_pagination_total_reflects_filters_not_just_the_page(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    for i in range(3):
        application = make_application(opening, candidate_name=f"Screening {i}")
        _touch(db_session, application, current_stage=Stage.SCREENING)
    make_application(opening, candidate_name="Still Applied")
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications", params={"stage": "screening", "page_size": 2}, headers=headers)
    body = response.json()
    assert body["total"] == 3
    assert len(body["results"]) == 2


def test_interviewer_forbidden_from_search(client, interviewer):
    headers = auth_headers(client, "interviewer@example.com")
    response = client.get("/applications", headers=headers)
    assert response.status_code == 403


def test_invalid_sort_value_returns_422(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/applications", params={"sort": "nonsense"}, headers=headers)
    assert response.status_code == 422


def test_page_size_over_max_returns_422(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/applications", params={"page_size": 1000}, headers=headers)
    assert response.status_code == 422


def test_page_below_one_returns_422(client, recruiter):
    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/applications", params={"page": 0}, headers=headers)
    assert response.status_code == 422
