"""
Demo data seed script. Run with `python -m app.seed`.

This is the only way accounts get created — README goal 1 says there is no
public signup for this internal tool. Beyond the demo users, this also
populates realistic job openings, applications, interview panels, feedback,
and two specifically-crafted stalled-alert scenarios (goal 10), all driven
through the real app/services/pipeline.py transitions rather than hand-
faked rows, so the resulting ApplicationHistoryEntry timeline looks exactly
like what the app itself would have produced.

Idempotent per application: an opening is matched by title, an application
by (opening, candidate_email). Re-running after a partial or prior seed
only creates what's missing — it never re-advances, re-assigns, or
duplicates feedback on an application that already exists.
"""
from datetime import datetime, timedelta, timezone

from app.auth import hash_password
from app.database import SessionLocal
from app.models import (
    Application,
    ApplicationHistoryEntry,
    ApplicationInterviewer,
    HistoryEventType,
    JobOpening,
    OpeningStatus,
    Stage,
    User,
    UserRole,
)
from app.services import pipeline

DEMO_USERS = [
    {
        "email": "recruiter@demo.com",
        "password": "RecruiterPass123!",
        "name": "Rachel Recruiter",
        "role": UserRole.RECRUITER,
    },
    {
        "email": "recruiter2@demo.com",
        "password": "RecruiterPass123!",
        "name": "Marcus Chen",
        "role": UserRole.RECRUITER,
    },
    {
        "email": "interviewer@demo.com",
        "password": "InterviewerPass123!",
        "name": "Ian Interviewer",
        "role": UserRole.INTERVIEWER,
    },
    {
        "email": "interviewer2@demo.com",
        "password": "InterviewerPass123!",
        "name": "Priya Nair",
        "role": UserRole.INTERVIEWER,
    },
]

OPENINGS = [
    {
        "key": "backend",
        "title": "Senior Backend Engineer",
        "department": "Engineering",
        "description": "Own core services powering the platform's API. 5+ years, strong Postgres and distributed-systems experience.",
        "status": OpeningStatus.OPEN,
        "archived": False,
    },
    {
        "key": "design",
        "title": "Product Designer",
        "department": "Design",
        "description": "End-to-end product design across web and mobile, from research through polished UI.",
        "status": OpeningStatus.OPEN,
        "archived": False,
    },
    {
        "key": "sales",
        "title": "Sales Development Representative",
        "department": "Sales",
        "description": "Outbound prospecting and qualification for the mid-market sales team.",
        "status": OpeningStatus.CLOSED,
        "archived": False,
    },
    {
        "key": "support",
        "title": "Support Specialist (Contract)",
        "department": "Customer Support",
        "description": "Six-month contract covering support ticket volume during a product launch.",
        "status": OpeningStatus.CLOSED,
        "archived": True,
    },
]

# Each entry: candidate_name, email, source, notes, days_ago (for created_at),
# and either "stage" (walk forward to here) or "reject_from" (walk forward to
# here, then reject). interviewers/feedback are lists of demo-user emails.
APPLICATIONS = {
    "backend": [
        dict(name="Devon Marsh", email="devon.marsh@example.com", source="referral",
             notes="5 yrs Go/Postgres experience.", days_ago=4, stage=Stage.APPLIED),
        dict(name="Priya Subramaniam", email="priya.subramaniam@example.com", source="LinkedIn",
             notes="Strong distributed systems background.", days_ago=2, stage=Stage.APPLIED),
        dict(name="Jordan Whitfield", email="jordan.whitfield@example.com", source="careers page",
             notes="", days_ago=6, stage=Stage.APPLIED),
        dict(name="Alicia Novak", email="alicia.novak@example.com", source="referral",
             notes="Referred by team lead.", days_ago=12, stage=Stage.SCREENING),
        dict(name="Marcus Bellweather", email="marcus.bellweather@example.com", source="indeed",
             notes="", days_ago=15, stage=Stage.SCREENING),
        dict(name="Sana Okafor", email="sana.okafor@example.com", source="LinkedIn",
             notes="Excellent system design skills in phone screen.", days_ago=20, stage=Stage.INTERVIEW,
             interviewers=["interviewer@demo.com", "interviewer2@demo.com"],
             feedback=[
                 ("interviewer@demo.com", "Strong on system design, asked great clarifying questions. Recommend moving forward."),
                 ("interviewer2@demo.com", "Communicated clearly under pressure. +1 to advance."),
             ]),
        dict(name="Tomas Reyes", email="tomas.reyes@example.com", source="referral",
             notes="", days_ago=28, stage=Stage.OFFER, interviewers=["interviewer2@demo.com"]),
        dict(name="Grace Lindqvist", email="grace.lindqvist@example.com", source="careers page",
             notes="Accepted offer, start date confirmed.", days_ago=45, stage=Stage.HIRED),
    ],
    "design": [
        dict(name="Farah Haddad", email="farah.haddad@example.com", source="LinkedIn",
             notes="", days_ago=3, stage=Stage.APPLIED),
        dict(name="Owen Kaczmarek", email="owen.kaczmarek@example.com", source="careers page",
             notes="Strong portfolio, mostly mobile work.", days_ago=11, stage=Stage.SCREENING),
        dict(name="Nadia Volkov", email="nadia.volkov@example.com", source="referral",
             notes="", days_ago=18, stage=Stage.INTERVIEW,
             interviewers=["interviewer@demo.com"],
             feedback=[("interviewer@demo.com", "Portfolio review went well. Design rationale was thoughtful and well-articulated.")]),
        dict(name="Kwame Asante", email="kwame.asante@example.com", source="indeed",
             notes="", days_ago=22, stage=Stage.INTERVIEW),
        dict(name="Lena Fischer", email="lena.fischer@example.com", source="LinkedIn",
             notes="Not enough enterprise UX experience.", days_ago=25, reject_from=Stage.SCREENING),
        dict(name="Ravi Chandran", email="ravi.chandran@example.com", source="referral",
             notes="Portfolio didn't match seniority level required.", days_ago=30, reject_from=Stage.INTERVIEW),
    ],
    "sales": [
        dict(name="Bianca Ferreira", email="bianca.ferreira@example.com", source="LinkedIn",
             notes="Great close rate at previous role.", days_ago=50, stage=Stage.HIRED),
        dict(name="Connor Blake", email="connor.blake@example.com", source="referral",
             notes="", days_ago=55, stage=Stage.HIRED),
        dict(name="Ines Duarte", email="ines.duarte@example.com", source="indeed",
             notes="Didn't pass the roleplay round.", days_ago=40, reject_from=Stage.INTERVIEW),
        dict(name="Hassan Malik", email="hassan.malik@example.com", source="careers page",
             notes="No prior SaaS sales experience.", days_ago=42, reject_from=Stage.SCREENING),
        dict(name="Wendy Tran", email="wendy.tran@example.com", source="LinkedIn",
             notes="Opening closed before follow-up.", days_ago=35, stage=Stage.APPLIED),
    ],
    "support": [
        dict(name="Diego Salgado", email="diego.salgado@example.com", source="indeed",
             notes="", days_ago=70, stage=Stage.HIRED),
        dict(name="Fatima Zahra", email="fatima.zahra@example.com", source="careers page",
             notes="Availability didn't match contract hours.", days_ago=65, reject_from=Stage.SCREENING),
        dict(name="Noah Petrov", email="noah.petrov@example.com", source="LinkedIn",
             notes="Not a fit for contract role.", days_ago=60, reject_from=Stage.APPLIED),
        dict(name="Yuki Tanaka", email="yuki.tanaka@example.com", source="referral",
             notes="Contract ended before decision made.", days_ago=68, stage=Stage.APPLIED),
    ],
}

STAGE_SEQUENCE = [Stage.APPLIED, Stage.SCREENING, Stage.INTERVIEW, Stage.OFFER, Stage.HIRED]
STALL_BACKDATE_DAYS = 15  # comfortably past goal 10's 10-day threshold


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_users(db) -> dict[str, User]:
    users = {}
    created = []
    for spec in DEMO_USERS:
        user = db.query(User).filter(User.email == spec["email"]).first()
        if user is None:
            user = User(
                email=spec["email"],
                password_hash=hash_password(spec["password"]),
                name=spec["name"],
                role=spec["role"],
            )
            db.add(user)
            db.flush()
            created.append(spec["email"])
        users[spec["email"]] = user
    db.commit()
    return users, created


def _get_or_create_opening(db, spec, recruiter) -> tuple[JobOpening, bool]:
    existing = db.query(JobOpening).filter(JobOpening.title == spec["title"]).first()
    if existing is not None:
        return existing, False
    opening = JobOpening(
        title=spec["title"],
        department=spec["department"],
        description=spec["description"],
        status=spec["status"],
        archived=spec["archived"],
        created_by_id=recruiter.id,
    )
    db.add(opening)
    db.commit()
    db.refresh(opening)
    return opening, True


def _get_or_create_application(db, opening, recruiter, spec, created_at) -> tuple[Application, bool]:
    existing = (
        db.query(Application)
        .filter(Application.job_opening_id == opening.id, Application.candidate_email == spec["email"])
        .first()
    )
    if existing is not None:
        return existing, False
    application = Application(
        job_opening_id=opening.id,
        candidate_name=spec["name"],
        candidate_email=spec["email"],
        source=spec["source"],
        notes=spec["notes"],
        current_stage=Stage.APPLIED,
        created_by_id=recruiter.id,
        created_at=created_at,
        updated_at=created_at,
        stage_changed_at=created_at,
    )
    db.add(application)
    db.flush()
    db.add(
        ApplicationHistoryEntry(
            application_id=application.id,
            event_type=HistoryEventType.CREATED,
            old_stage=None,
            new_stage=Stage.APPLIED,
            actor_id=recruiter.id,
            created_at=created_at,
        )
    )
    db.commit()
    db.refresh(application)
    return application, True


def _advance_to(db, application, target_stage, actor) -> None:
    target_index = STAGE_SEQUENCE.index(target_stage)
    while STAGE_SEQUENCE.index(application.current_stage) < target_index:
        next_stage = pipeline.next_stage_after(application.current_stage)
        db.add(pipeline.advance(application, next_stage, actor))
    db.commit()


def _reject_from(db, application, from_stage, actor) -> None:
    _advance_to(db, application, from_stage, actor)
    db.add(pipeline.reject(application, actor))
    db.commit()


def _assign_interviewer(db, application, interviewer) -> None:
    exists = (
        db.query(ApplicationInterviewer)
        .filter(
            ApplicationInterviewer.application_id == application.id,
            ApplicationInterviewer.interviewer_id == interviewer.id,
        )
        .first()
    )
    if exists is None:
        db.add(ApplicationInterviewer(application_id=application.id, interviewer_id=interviewer.id))
        db.commit()


def _leave_feedback(db, application, interviewer, text) -> None:
    db.add(
        ApplicationHistoryEntry(
            application_id=application.id,
            event_type=HistoryEventType.FEEDBACK,
            old_stage=None,
            new_stage=None,
            feedback_text=text,
            actor_id=interviewer.id,
        )
    )
    db.commit()


def _seed_applications(db, users, recruiter) -> dict[str, int]:
    counts = {"openings_created": 0, "applications_created": 0}
    for opening_spec in OPENINGS:
        opening, opening_created = _get_or_create_opening(db, opening_spec, recruiter)
        if opening_created:
            counts["openings_created"] += 1

        for app_spec in APPLICATIONS[opening_spec["key"]]:
            created_at = _now() - timedelta(days=app_spec["days_ago"])
            application, app_created = _get_or_create_application(db, opening, recruiter, app_spec, created_at)
            if not app_created:
                continue
            counts["applications_created"] += 1

            if "reject_from" in app_spec:
                _reject_from(db, application, app_spec["reject_from"], recruiter)
            else:
                _advance_to(db, application, app_spec["stage"], recruiter)

            for interviewer_email in app_spec.get("interviewers", []):
                _assign_interviewer(db, application, users[interviewer_email])
            for interviewer_email, text in app_spec.get("feedback", []):
                _leave_feedback(db, application, users[interviewer_email], text)

    return counts


def _seed_stalled_alert_demo(db, opening, recruiter) -> dict[str, bool]:
    """
    Goal 10, made visible: one application that's simply been sitting
    untouched, and one that was dismissed, moved on, and stalled again —
    proving the reappearance rule with real seeded data, not just tests.
    """
    result = {"stalled_created": False, "reappeared_created": False}

    stalled_spec = dict(
        name="Stalled Candidate — Needs Follow-up",
        email="stalled.demo@example.com",
        source="referral",
        notes="Sat untouched after applying — seeded to demonstrate goal 10's stalled-alert detection.",
    )
    stalled_created_at = _now() - timedelta(days=STALL_BACKDATE_DAYS + 3)
    stalled, created = _get_or_create_application(db, opening, recruiter, stalled_spec, stalled_created_at)
    if created:
        stalled.stage_changed_at = _now() - timedelta(days=STALL_BACKDATE_DAYS)
        db.commit()
        result["stalled_created"] = True

    reappeared_spec = dict(
        name="Reappeared Alert Candidate",
        email="reappeared.demo@example.com",
        source="LinkedIn",
        notes="Dismissed once while stalled, then advanced and stalled again — seeded to demonstrate goal 10's reappearance rule.",
    )
    reappeared_created_at = _now() - timedelta(days=STALL_BACKDATE_DAYS + 10)
    reappeared, created = _get_or_create_application(db, opening, recruiter, reappeared_spec, reappeared_created_at)
    if created:
        # Advance once, then simulate it stalling in Screening.
        _advance_to(db, reappeared, Stage.SCREENING, recruiter)
        reappeared.stage_changed_at = _now() - timedelta(days=STALL_BACKDATE_DAYS)
        db.commit()

        # Dismiss it — exactly what the /dismiss-alert endpoint does.
        reappeared.stall_dismissed_at = _now()
        reappeared.stall_dismissed_stage = reappeared.current_stage
        db.commit()

        # Advance again — goal 4's transition logic clears the dismissal.
        _advance_to(db, reappeared, Stage.INTERVIEW, recruiter)

        # Simulate it stalling again, in the new stage. Since the dismissal
        # was cleared on advance, this should reappear as a fresh alert.
        reappeared.stage_changed_at = _now() - timedelta(days=STALL_BACKDATE_DAYS)
        db.commit()
        result["reappeared_created"] = True

    return result


def seed() -> None:
    db = SessionLocal()
    try:
        users, created_user_emails = _create_users(db)
        recruiter = users["recruiter@demo.com"]

        counts = _seed_applications(db, users, recruiter)

        backend_opening = db.query(JobOpening).filter(JobOpening.title == "Senior Backend Engineer").first()
        alert_result = _seed_stalled_alert_demo(db, backend_opening, recruiter)
    finally:
        db.close()

    print("Demo credentials:")
    for spec in DEMO_USERS:
        status = "created" if spec["email"] in created_user_emails else "already existed"
        print(f"  {spec['role'].value:12s} {spec['email']:25s} {spec['password']:20s} ({status})")

    print()
    print("Seed data:")
    print(f"  Job openings created this run: {counts['openings_created']} (of {len(OPENINGS)} total)")
    print(f"  Applications created this run: {counts['applications_created']} "
          f"(of {sum(len(v) for v in APPLICATIONS.values()) + 2} total, including the 2 alerts-demo applications)")
    print(f"  Stalled-alert demo application: {'created' if alert_result['stalled_created'] else 'already existed'}")
    print(f"  Reappeared-alert demo application: {'created' if alert_result['reappeared_created'] else 'already existed'}")


if __name__ == "__main__":
    seed()
