"""
Demo data seed script. Run with `python -m app.seed`.

This is the only way accounts get created — README goal 1 says there is no
public signup for this internal tool, so a recruiter and interviewer with
fixed, known credentials are the starting point for logging in and demoing
the app after a fresh migration.
"""
from app.auth import hash_password
from app.database import SessionLocal
from app.models import User, UserRole

DEMO_USERS = [
    {
        "email": "recruiter@demo.com",
        "password": "RecruiterPass123!",
        "name": "Rachel Recruiter",
        "role": UserRole.RECRUITER,
    },
    {
        "email": "interviewer@demo.com",
        "password": "InterviewerPass123!",
        "name": "Ian Interviewer",
        "role": UserRole.INTERVIEWER,
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        created_emails = set()
        for spec in DEMO_USERS:
            existing = db.query(User).filter(User.email == spec["email"]).first()
            if existing is None:
                db.add(
                    User(
                        email=spec["email"],
                        password_hash=hash_password(spec["password"]),
                        name=spec["name"],
                        role=spec["role"],
                    )
                )
                created_emails.add(spec["email"])
        db.commit()
    finally:
        db.close()

    print("Demo credentials:")
    for spec in DEMO_USERS:
        status = "created" if spec["email"] in created_emails else "already existed"
        print(f"  {spec['role'].value:12s} {spec['email']:25s} {spec['password']:20s} ({status})")


if __name__ == "__main__":
    seed()
