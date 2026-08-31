"""
Password hashing (bcrypt) and JWT issuing/verification. Kept deliberately
small and dependency-light: bcrypt directly, PyJWT directly, no passlib
indirection layer (see docs/decisions.md).
"""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import get_settings

settings = get_settings()

# bcrypt has a hard 72-byte input limit; truncate defensively rather than
# letting bcrypt silently ignore bytes past 72 or raise on some builds.
_BCRYPT_MAX_BYTES = 72


def hash_password(plain_password: str) -> str:
    truncated = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(truncated, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, password_hash: str) -> bool:
    truncated = plain_password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.checkpw(truncated, password_hash.encode("utf-8"))


def create_access_token(*, user_id: int, role: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": str(user_id), "role": role, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Raises jwt.PyJWTError (or a subclass) if the token is invalid/expired."""
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
