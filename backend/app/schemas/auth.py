import re

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import UserRole

# Pydantic's EmailStr needs the extra `email-validator` package, which isn't
# in the approved dependency list — a plain regex check is enough for this
# app's needs without adding another dependency.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_email_format(value: str) -> str:
    value = value.strip().lower()
    if not _EMAIL_RE.match(value):
        raise ValueError("Not a valid email address.")
    return value


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def _check_email(cls, v: str) -> str:
        return validate_email_format(v)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: UserRole


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
