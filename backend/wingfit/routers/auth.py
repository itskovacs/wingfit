from typing import Annotated

import jwt
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlmodel import select
import json
import httpx
from ..config import settings
from ..db.core import init_user_data
from ..deps import SessionDep, get_current_username
from ..models.models import (
    LoginRegisterModel,
    AuthParams,
    Token,
    UpdateUserPassword,
    User,
)
from ..security import (
    create_access_token,
    create_tokens,
    hash_password,
    verify_password,
    generate_mfa_secret,
    verify_mfa_code,
)
from ..utils.logging import app_logger
from ..utils.date import dt_utc, dt_utc_offset
from ..utils.misc import generate_api_token

router = APIRouter(prefix="/api/auth", tags=["auth"])
pending_mfa_usernames = {}


@router.get("/params", response_model=AuthParams)
async def auth_params() -> AuthParams:
    data = {"auth": settings.AUTH_METHOD, "oidc": None, "register_enabled": settings.REGISTER_ENABLE}

    if settings.AUTH_METHOD == "oidc":
        data["oidc"] = {
            "OIDC_HOST": settings.OIDC_HOST,
            "OIDC_REALM": settings.OIDC_REALM,
            "OIDC_CLIENT_ID": settings.OIDC_CLIENT_ID,
            "OIDC_REDIRECT_URI": settings.OIDC_REDIRECT_URI,
        }

    return data


@router.post("/login")
async def login(req: LoginRegisterModel, session: SessionDep):
    if settings.AUTH_METHOD == "oidc":
        app_logger.error("[login] Local Authentication is disabled")
        raise HTTPException(status_code=400, detail="Bad request")

    db_user = session.get(User, req.username)
    if not db_user or not verify_password(req.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not db_user.is_active:
        raise HTTPException(status_code=401, detail="User is disabled")

    if db_user.mfa_enabled:
        pending_mfa_code = generate_mfa_secret()
        pending_mfa_usernames[db_user.username] = {"pending_code": pending_mfa_code, "exp": dt_utc_offset(5)}

        return {"pending_code": pending_mfa_code, "username": db_user.username}

    return create_tokens(data={"sub": db_user.username})


@router.post("/login_mfa", response_model=Token)
async def verify_mfa(
    session: SessionDep,
    username: str = Body(..., embed=True),
    pending_code: str = Body(..., embed=True),
    code: str = Body(..., embed=True),
) -> Token:
    user = session.get(User, username)
    if not user or not user.mfa_enabled:
        raise HTTPException(status_code=401, detail="Invalid MFA flow")

    record = pending_mfa_usernames.get(username)
    if not record or record["exp"] < dt_utc() or record["pending_code"] != pending_code:
        pending_mfa_usernames.pop(username, None)
        raise HTTPException(status_code=401, detail="Unauthorized")

    if not verify_mfa_code(user.mfa_secret, code):
        raise HTTPException(status_code=403, detail="Invalid MFA code")

    return create_tokens({"sub": user.username})


@router.post("/register", response_model=Token)
async def register(req: LoginRegisterModel, session: SessionDep) -> Token:
    if not settings.REGISTER_ENABLE:
        raise HTTPException(status_code=400, detail="Registration disabled")

    if settings.AUTH_METHOD == "oidc":
        app_logger.error("[login] Local Authentication is disabled")
        raise HTTPException(status_code=400, detail="Bad request")

    user = session.get(User, req.username)
    if user:
        raise HTTPException(status_code=409, detail="The resource already exists")

    is_first = not session.execute(select(User).limit(1)).first()

    new_user = User(username=req.username, password=hash_password(req.password), is_su=is_first)
    session.add(new_user)
    session.commit()

    init_user_data(session, new_user.username)

    return create_tokens(data={"sub": new_user.username})


@router.post("/update_password")
async def auth_update_password(
    data: UpdateUserPassword,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
):
    if settings.AUTH_METHOD == "oidc":
        raise HTTPException(status_code=400, detail="Bad request")

    db_user = session.get(User, current_user)

    if not verify_password(data.current, db_user.password):
        raise HTTPException(status_code=403, detail="Invalid credentials")

    db_user.password = hash_password(data.new)
    session.add(db_user)
    session.commit()

    return {}


@router.post("/refresh")
async def refresh_token(refresh_token: str = Body(..., embed=True)):
    if not refresh_token:
        app_logger.error("[refresh_token] Refresh Token not found")
        raise HTTPException(status_code=400, detail="Bad request")

    try:
        payload = jwt.decode(refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub", None)

        if username is None:
            raise HTTPException(status_code=401, detail="Invalid Token")

        new_access_token = create_access_token(data={"sub": username})

        return {"access_token": new_access_token}

    except jwt.ExpiredSignatureError:
        app_logger.error("[refresh_token] Refresh Token is expired")
        raise HTTPException(status_code=401, detail="Invalid Token")
    except jwt.PyJWTError as exc:
        app_logger.error(f"[refresh_token] PyJWT Error: {exc}")
        raise HTTPException(status_code=401, detail="Invalid Token")


@router.post("/oidc/login", response_model=Token)
async def oidc_login(session: SessionDep, code: str = Body(..., embed=True)) -> Token:
    if settings.AUTH_METHOD != "oidc":
        raise HTTPException(status_code=400, detail="Bad request")

    discovery_url = (
        f"http://{settings.OIDC_HOST}/realms/{settings.OIDC_REALM}/.well-known/openid-configuration"
    )
    async with httpx.AsyncClient() as client:
        discovery_resp = await client.get(discovery_url)
        if discovery_resp.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to load OIDC configuration")
        config = discovery_resp.json()

    token_url = config["token_endpoint"]
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "client_id": settings.OIDC_CLIENT_ID,
        "client_secret": settings.OIDC_CLIENT_SECRET,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url, data=data, headers=headers)
        if token_resp.status_code != 200:
            raise HTTPException(status_code=401, detail="Failed to exchange code for tokens")
        token_data = token_resp.json()

    id_token = token_data.get("id_token")
    alg = jwt.get_unverified_header(id_token).get("alg")

    if alg == "HS256":
        decoded = jwt.decode(
            id_token,
            settings.OIDC_CLIENT_SECRET,
            algorithms=alg,
            audience=settings.OIDC_CLIENT_ID,
        )
    elif alg == "RS256":
        jwks_uri = config.get("jwks_uri")
        if not jwks_uri:
            raise HTTPException(status_code=400, detail="Bad request")

        async with httpx.AsyncClient() as client:
            jwk = await client.get(jwks_uri)
            if token_resp.status_code != 200:
                raise HTTPException(status_code=400, detail="Bad request")
            jwks = jwk.json().get("keys")

        public_keys = {}
        for jwk in jwks:
            kid = jwk.get("kid")
            if not kid:
                continue
            public_keys[kid] = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(jwk))
        kid = jwt.get_unverified_header(id_token).get("kid")
        pk = public_keys.get(kid)

        decoded = jwt.decode(
            id_token,
            key=pk,
            algorithms=alg,
            audience=settings.OIDC_CLIENT_ID,
        )

    username = decoded.get("preferred_username")
    if not username:
        raise HTTPException(status_code=400, detail="Username not found in user info")

    user = session.get(User, username)
    if not user:
        # TODO: password is non-null, we must init the pw with something, the model is not made for OIDC
        user = User(username=username, password=hash_password(generate_api_token()))
        session.add(user)
        session.commit()
        init_user_data(session, username)

    return create_tokens(data={"sub": username})
