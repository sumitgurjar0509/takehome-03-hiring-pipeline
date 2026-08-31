"""
Shared FastAPI dependencies. This is where server-side authorization is
enforced — every route that needs a logged-in user, or a specific role,
pulls one of these in rather than checking anything in the frontend.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.auth import decode_access_token
from app.database import get_db
from app.models import User, UserRole

# tokenUrl is only used to render the "Authorize" button in the interactive
# /docs UI; the real login endpoint takes a JSON body, not an OAuth2 form.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_error
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        raise credentials_error

    user = db.get(User, user_id)
    if user is None:
        raise credentials_error
    return user


def require_recruiter(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.RECRUITER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is restricted to recruiters.",
        )
    return user


def require_interviewer(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.INTERVIEWER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action is restricted to interviewers.",
        )
    return user
