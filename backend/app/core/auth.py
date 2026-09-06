from datetime import UTC, datetime, timedelta

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.db.models import User
from app.db.session import get_db
from app.settings import Settings, get_settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer = HTTPBearer(auto_error=False)
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def create_access_token(user: User, settings: Settings) -> str:
    expires_at = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user.id), "role": user.role, "exp": expires_at},
        settings.app_secret,
        algorithm=ALGORITHM,
    )


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    database: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(credentials.credentials, settings.app_secret, algorithms=[ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, TypeError, ValueError) as exc:
        raise unauthorized from exc
    user = database.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


def require_role(*roles: str):
    def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return dependency
