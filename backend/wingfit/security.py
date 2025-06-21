from datetime import UTC, datetime, timedelta

import pyotp
import jwt
from argon2 import PasswordHasher
from argon2 import exceptions as argon_exceptions
from fastapi import HTTPException
from sqlmodel import Session, select

from .config import settings
from .models.models import Token, User
from .utils.logging import app_logger

ph = PasswordHasher()


def generate_mfa_secret() -> str:
    return pyotp.random_base32()


def verify_mfa_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    return totp.verify(code)


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except (
        argon_exceptions.VerifyMismatchError,
        argon_exceptions.VerificationError,
        argon_exceptions.InvalidHashError,
    ) as exc:
        app_logger.error(f"[verify_password] Exception: {exc}")
        raise HTTPException(status_code=401, detail="Invalid credentials")


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire.timestamp()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_tokens(data: dict) -> Token:
    return Token(access_token=create_access_token(data), refresh_token=create_refresh_token(data))


async def ensure_superuser(session: Session, username: str) -> None:
    user = session.get(User, username)
    if not user.is_su:
        raise HTTPException(status_code=401, detail="Unauthorized")


def verify_exists_and_owns(username: str, obj) -> None:
    if not obj:
        raise HTTPException(status_code=404, detail="The resource does not exist")

    if obj.user != username:
        raise PermissionError

    return None


def api_token_to_user(session: Session, api_token: str) -> User | None:
    if not api_token:
        return None

    user = session.exec(select(User).where(User.api_token == api_token)).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Token")
    return user
