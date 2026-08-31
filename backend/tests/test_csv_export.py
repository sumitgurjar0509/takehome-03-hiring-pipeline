import csv
import io

from app.models import OpeningStatus, Stage
from tests.conftest import auth_headers


def _touch(db_session, application, **fields):
    for key, value in fields.items():
        setattr(application, key, value)
    db_session.commit()
    db_session.refresh(application)


def _parse_csv(text: str) -> list[dict]:
    return list(csv.DictReader(io.StringIO(text)))


def test_csv_export_excludes_hired_and_rejected(
    client, recruiter, make_opening, make_application, db_session
):
    opening = make_opening()
    applied = make_application(opening, candidate_name="Still Applied")
    screening = make_application(opening, candidate_name="In Screening")
    _touch(db_session, screening, current_stage=Stage.SCREENING)
    hired = make_application(opening, candidate_name="Got Hired")
    _touch(db_session, hired, current_stage=Stage.HIRED)
    rejected = make_application(opening, candidate_name="Got Rejected")
    _touch(db_session, rejected, current_stage=Stage.REJECTED, rejected_from_stage=Stage.OFFER)

    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/applications/export", headers=headers)
    assert response.status_code == 200

    rows = _parse_csv(response.text)
    names = {row["Candidate Name"] for row in rows}
    assert applied.candidate_name in names
    assert screening.candidate_name in names
    assert hired.candidate_name not in names
    assert rejected.candidate_name not in names


def test_csv_export_includes_applications_regardless_of_opening_status(
    client, recruiter, make_opening, make_application
):
    open_opening = make_opening(title="Open Opening")
    closed_opening = make_opening(title="Closed Opening", status=OpeningStatus.CLOSED)
    archived_opening = make_opening(title="Archived Opening", archived=True)

    from_open = make_application(open_opening, candidate_name="From Open")
    from_closed = make_application(closed_opening, candidate_name="From Closed")
    from_archived = make_application(archived_opening, candidate_name="From Archived")

    headers = auth_headers(client, "recruiter@example.com")
    response = client.get("/applications/export", headers=headers)
    assert response.status_code == 200

    rows = _parse_csv(response.text)
    names = {row["Candidate Name"] for row in rows}
    assert from_open.candidate_name in names
    assert from_closed.candidate_name in names
    assert from_archived.candidate_name in names


def test_csv_export_has_required_columns(client, recruiter, make_opening, make_application):
    opening = make_opening()
    application = make_application(opening, candidate_name="Column Check", source="referral")
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications/export", headers=headers)
    assert response.status_code == 200

    rows = _parse_csv(response.text)
    assert set(rows[0].keys()) >= {
        "Candidate Name",
        "Candidate Email",
        "Job Opening",
        "Stage",
        "Applied Date",
    }
    row = next(r for r in rows if r["Candidate Name"] == "Column Check")
    assert row["Candidate Email"] == application.candidate_email
    assert row["Job Opening"] == opening.title
    assert row["Stage"] == "Applied"
    assert row["Applied Date"] == application.created_at.strftime("%Y-%m-%d")


def test_csv_export_content_type_and_filename(client, recruiter, make_opening, make_application):
    opening = make_opening()
    make_application(opening)
    headers = auth_headers(client, "recruiter@example.com")

    response = client.get("/applications/export", headers=headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "applications.csv" in response.headers["content-disposition"]


def test_interviewer_forbidden_from_csv_export(client, interviewer):
    headers = auth_headers(client, "interviewer@example.com")
    response = client.get("/applications/export", headers=headers)
    assert response.status_code == 403
