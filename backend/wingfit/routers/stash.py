from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlmodel import delete, select

from ..deps import SessionDep, get_current_username
from ..models.models import Stash, StashBase, StashRead
from ..security import api_token_to_user, verify_exists_and_owns

router = APIRouter(prefix="/api/stash", tags=["stash"])


@router.get("", response_model=list[StashRead])
def get_stash(
    session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]
) -> list[StashRead]:
    stash = session.exec(select(Stash).filter(Stash.user == current_user))
    return [StashRead.serialize(elem) for elem in stash]


@router.post("")
def post_stash(
    stash_data: StashBase,
    session: SessionDep,
    X_Api_Token: Annotated[str | None, Header()] = None,
) -> dict:
    user = api_token_to_user(session, X_Api_Token)
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized")

    new_stash = Stash(content=stash_data.content, user=user.username)
    session.add(new_stash)
    session.commit()
    session.refresh(new_stash)
    return {}


@router.delete("/{stash_id}")
def delete_stash(
    session: SessionDep,
    stash_id: int,
    current_user: Annotated[str, Depends(get_current_username)],
) -> dict:
    db_stash = session.get(Stash, stash_id)
    verify_exists_and_owns(current_user, db_stash)

    session.delete(db_stash)
    session.commit()
    return {}


@router.delete("")
def empty_stash(session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]) -> dict:
    session.exec(delete(Stash).where(Stash.user == current_user))
    session.commit()
    return {}
