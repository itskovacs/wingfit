from datetime import datetime
from typing import Annotated
import pyotp

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlmodel import select

from .. import __version__
from ..security import generate_mfa_secret, verify_mfa_code
from ..deps import SessionDep, get_current_username
from sqlalchemy.orm import selectinload
from ..models.models import (
    Bloc,
    BlocCategory,
    BlocCategoryRead,
    BlocRead,
    HealthWatchData,
    HealthWatchDataRead,
    Program,
    PR,
    PRRead,
    User,
    UserRead,
)
from ..utils.misc import check_update, generate_api_token
from .programs import export_program

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=UserRead)
async def get_user_settings(
    session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]
) -> UserRead:
    db_user = session.get(User, current_user)
    return UserRead.serialize(db_user)


@router.put("/export")
async def export_user_data(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    code: str = Body(..., embed=True),
):
    db_user = session.get(User, current_user)
    if not db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Enable MFA to export data")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid code")

    data = {
        "_": {"at": datetime.timestamp(datetime.now()), "version": __version__},
        "categories": [
            BlocCategoryRead.serialize(c)
            for c in session.exec(select(BlocCategory).filter(BlocCategory.user == current_user))
        ],
        "pr": [
            PRRead.serialize(pr)
            for pr in session.exec(
                select(PR).where(PR.user == current_user).options(selectinload(PR.values))
            )
        ],
        "blocs": [
            BlocRead.serialize(bloc) for bloc in session.exec(select(Bloc).filter(Bloc.user == current_user))
        ],
        "programs": [
            await export_program(program.id, session, current_user)
            for program in session.exec(select(Program).filter(Program.user == current_user))
        ],
    }

    hw_data = session.exec(
        select(HealthWatchData)
        .where(HealthWatchData.user == current_user)
        .order_by(HealthWatchData.cdate.desc())
    )
    data["hw_data"] = [HealthWatchDataRead.serialize(r) for r in hw_data]

    return data


@router.get("/checkversion")
def check_version(session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]):
    return check_update()


@router.put("/api_token")
def generate_user_api_token(
    session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]
) -> str:
    db_user = session.get(User, current_user)
    if db_user.api_token:
        raise HTTPException(status_code=400, detail="Bad request")

    token = generate_api_token()
    setattr(db_user, "api_token", token)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return token


@router.delete("/api_token")
def delete_user_api_token(session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]):
    db_user = session.get(User, current_user)
    if not db_user.api_token:
        raise HTTPException(status_code=400, detail="Bad request")

    setattr(db_user, "api_token", None)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return {}


@router.post("/mfa/enable")
async def enable_mfa(session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]):
    db_user = session.get(User, current_user)
    if not db_user:
        raise HTTPException(status_code=404, detail="The resource does not exist")

    if db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Bad request")

    mfa_secret = generate_mfa_secret()
    db_user.mfa_secret = mfa_secret
    session.add(db_user)
    session.commit()

    totp = pyotp.TOTP(mfa_secret)
    uri = totp.provisioning_uri(name=db_user.username, issuer_name="Wingfit")

    return {"secret": mfa_secret, "uri": uri}


@router.post("/mfa/verify")
async def verify_mfa(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    code: str = Body(..., embed=True),
):
    db_user = session.get(User, current_user)
    if not db_user:
        raise HTTPException(status_code=404, detail="The resource does not exist")

    if not db_user.mfa_secret or db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Bad request")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        db_user.mfa_secret = None
        session.add(db_user)
        session.commit()
        raise HTTPException(status_code=403, detail="Invalid code")

    db_user.mfa_enabled = True
    session.add(db_user)
    session.commit()

    return {}


@router.post("/mfa/disable")
async def disable_mfa(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    code: str = Body(..., embed=True),
):
    db_user = session.get(User, current_user)
    if not db_user or not db_user.mfa_enabled or not db_user.mfa_secret:
        raise HTTPException(status_code=400, detail="Bad request")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid code")

    db_user.mfa_secret = None
    db_user.mfa_enabled = False

    session.add(db_user)
    session.commit()

    return {}
