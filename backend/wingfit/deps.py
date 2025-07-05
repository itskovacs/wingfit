from typing import Annotated

import jwt
from fastapi import Depends, Header, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session

from .config import settings
from .db.core import get_engine
from .models.models import User
from .security import api_token_to_user

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


def get_session():
    engine = get_engine()
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


def resolve_user_from_token(token: str, session: SessionDep) -> str:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid Token")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid Token")

    user = session.get(User, username)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid Token")
    return user.username


def get_current_username(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep) -> str:
    return resolve_user_from_token(token, session)


async def get_username_with_token_support(
    session: SessionDep,
    token: Annotated[str | None, Depends(oauth2_scheme)] = None,
    X_Api_Token: Annotated[str | None, Header()] = None,
) -> str:
    if token:
        try:
            return resolve_user_from_token(token, session)
        except HTTPException:
            pass

    if X_Api_Token:
        user = api_token_to_user(session, X_Api_Token)
        if user:
            return user.username

    raise HTTPException(status_code=401, detail="Unauthorized")
