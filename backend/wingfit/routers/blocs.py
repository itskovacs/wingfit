from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ..deps import SessionDep, get_current_username
from ..models.models import (
    Bloc,
    BlocCreate,
    BlocRead,
    BlocResult,
    BlocResultBase,
    BlocResultRead,
    BlocUpdate,
)
from ..security import verify_exists_and_owns
from ..utils.date import parse_str_or_date_to_date
from ..utils.logging import app_logger

router = APIRouter(prefix="/api/blocs", tags=["blocs"])


@router.get("", response_model=list[BlocRead])
async def get_blocs(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    startdate: str | None = None,
    enddate: str | None = None,
    limit: int = 0,
    offset: int = 0,
) -> list[BlocRead]:
    startdate = parse_str_or_date_to_date(startdate) if startdate else None
    enddate = parse_str_or_date_to_date(enddate) if enddate else None
    if startdate and enddate and startdate > enddate:
        app_logger.error(f"[get_blocs][{current_user}] Specified dates are incoherent")
        raise HTTPException(status_code=400, detail="Bad request")

    query = select(Bloc).where(Bloc.user == current_user).options(selectinload(Bloc.category))
    if startdate:
        query = query.where(Bloc.cdate >= startdate)

    if enddate:
        query = query.where(Bloc.cdate <= enddate)

    if offset:
        query = query.offset(offset)

    if limit:
        query = query.limit(limit)

    blocs = session.exec(query)
    return [BlocRead.serialize(bloc) for bloc in blocs]


@router.post("", response_model=BlocRead | list[BlocRead])
async def post_bloc(
    bloc_data: BlocCreate | list[BlocCreate],
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> BlocRead | list[BlocRead]:
    if not isinstance(bloc_data, list):
        bloc_data = [bloc_data]

    blocs = []
    for bloc in bloc_data:
        if not bloc.category and not bloc.category_id:
            app_logger.error(f"[post_bloc][{current_user}] No Category/Category_id provided")
            raise HTTPException(status_code=400, detail="Bad request")

        new_bloc = Bloc(
            content=bloc.content,
            duration=bloc.duration,
            cdate=parse_str_or_date_to_date(bloc.cdate),
            user=current_user,
        )

        # category_id prioritized
        if bloc.category_id:
            new_bloc.category_id = bloc.category_id

        # Else we retrieve category.id for bloc.category_id
        else:
            new_bloc.category_id = bloc.category.id

        session.add(new_bloc)
        blocs.append(new_bloc)

    session.commit()
    if len(blocs) == 1:
        return BlocRead.serialize(blocs[0])
    return [BlocRead.serialize(bloc) for bloc in blocs]


@router.put("/{bloc_id}", response_model=BlocRead)
async def put_bloc(
    session: SessionDep,
    bloc_id: int,
    bloc: BlocUpdate,
    current_user: Annotated[str, Depends(get_current_username)],
) -> BlocRead:
    db_bloc = session.get(Bloc, bloc_id)
    verify_exists_and_owns(current_user, db_bloc)

    bloc_data = bloc.model_dump(exclude_unset=True)
    if bloc_data.get("category"):
        bloc_data["category_id"] = bloc_data.get("category").get("id")
        bloc_data.pop("category")

    if bloc_data.get("cdate"):
        bloc_data["cdate"] = parse_str_or_date_to_date(bloc_data.get("cdate"))

    for key, value in bloc_data.items():
        setattr(db_bloc, key, value)

    session.add(db_bloc)
    session.commit()
    session.refresh(db_bloc)
    return BlocRead.serialize(db_bloc)


@router.delete("/{bloc_id}")
async def delete_bloc(
    session: SessionDep,
    bloc_id: int,
    current_user: Annotated[str, Depends(get_current_username)],
) -> dict:
    db_bloc = session.get(Bloc, bloc_id)
    verify_exists_and_owns(current_user, db_bloc)

    session.delete(db_bloc)
    session.commit()
    return {}


@router.put("/{bloc_id}/result", response_model=BlocResultRead)
async def put_bloc_result(
    bloc_id: int,
    result: BlocResultBase,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> BlocResultRead:
    # Used for POST and PUT, as I ensure the frontend always sends the full object

    db_bloc = session.get(Bloc, bloc_id)
    verify_exists_and_owns(current_user, db_bloc)

    new_result = BlocResult(key=result.key, value=result.value, comment=result.comment)
    session.add(new_result)
    db_bloc.result = new_result

    session.commit()
    session.refresh(db_bloc)
    return BlocResultRead.serialize(new_result)


@router.delete("/{bloc_id}/result")
async def delete_bloc_result(
    bloc_id: int,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> dict:
    db_bloc = session.get(Bloc, bloc_id)
    verify_exists_and_owns(current_user, db_bloc)

    if not db_bloc.result:
        raise HTTPException(status_code=404, detail="The resource does not exist")

    session.delete(db_bloc.result)
    db_bloc.result = None
    session.commit()
    return {}
