from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import selectinload
from sqlmodel import select

from ..deps import SessionDep, get_current_username
from ..models.models import (
    PR,
    PRCreate,
    PRRead,
    PRUpdate,
    PRValue,
    PRValueCreateOrUpdate,
    PRValueRead,
    ResultKeyEnum,
)
from ..security import verify_exists_and_owns
from ..utils.date import parse_str_or_date_to_date
from ..utils.logging import app_logger

router = APIRouter(prefix="/api/pr", tags=["pr"])


@router.get("", response_model=list[PRRead])
def get_prs(
    session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]
) -> list[PRRead]:
    prs = session.exec(select(PR).where(PR.user == current_user).options(selectinload(PR.values)))
    return [PRRead.serialize(pr) for pr in prs]


@router.post("", response_model=PRRead)
def post_pr(
    pr_data: PRCreate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> PRRead:
    new_pr = PR(name=pr_data.name, key=pr_data.key, user=current_user)
    if pr_data.key not in {item.value for item in ResultKeyEnum}:
        app_logger.error(f"[post_pr][{current_user}] Invalid key provided")
        raise HTTPException(status_code=400, detail="Bad request")

    if pr_data.values:
        pr_values = []
        for value in pr_data.values:
            try:
                parsed_date = parse_str_or_date_to_date(value.cdate)
                if parsed_date > date.today():
                    app_logger.error(f"[post_pr][{current_user}] PR Value cannot be in the future")
                    raise HTTPException(status_code=400, detail="Bad request")

                if not PRValueCreateOrUpdate.value_matches_record_key(new_pr.key, value.value):
                    app_logger.error(f"[post_pr][{current_user}] Invalid value for PR")
                    raise HTTPException(status_code=400, detail="Bad request")

                pr_values.append(PRValue(value=value.value, cdate=parsed_date, pr=new_pr))
            except ValueError as exc:
                app_logger.error(f"[post_pr][{current_user}] Error during PR value parsing: {exc}")
                raise HTTPException(status_code=400, detail="Bad request")

        new_pr.values = pr_values

    session.add(new_pr)
    session.commit()
    session.refresh(new_pr)
    return PRRead.serialize(new_pr)


@router.put("/{pr_id}", response_model=PRRead)
def put_pr(
    pr_id: int,
    pr_data: PRUpdate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> PRRead:
    db_pr = session.get(PR, pr_id)
    verify_exists_and_owns(current_user, db_pr)

    pr_data = pr_data.model_dump(exclude_unset=True)

    if pr_data.get("key") and (pr_data.key not in {item.value for item in ResultKeyEnum}):
        raise HTTPException(status_code=400, detail="Bad request")

    for key, value in pr_data.items():
        setattr(db_pr, key, value)

    session.add(db_pr)
    session.commit()
    session.refresh(db_pr)
    return PRRead.serialize(db_pr)


@router.delete("/{pr_id}")
def delete_pr(
    pr_id: int,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> dict:
    db_pr = session.get(PR, pr_id)
    verify_exists_and_owns(current_user, db_pr)
    session.delete(db_pr)
    session.commit()
    return {}


@router.post("/{pr_id}/values", response_model=list[PRValueRead])
def post_pr_value(
    pr_id: int,
    value_data: PRValueCreateOrUpdate | list[PRValueCreateOrUpdate],
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> list[PRValueRead]:
    db_pr = session.get(PR, pr_id)
    verify_exists_and_owns(current_user, db_pr)

    if not isinstance(value_data, list):
        value_data = [value_data]

    values = []
    for value in value_data:
        try:
            parsed_date = parse_str_or_date_to_date(value.cdate)
            if parsed_date > date.today():
                app_logger.error(f"[post_pr_value][{current_user}] PR Value cannot be in the future")
                raise HTTPException(status_code=400, detail="Bad request")

            if not PRValueCreateOrUpdate.value_matches_record_key(db_pr.key, value.value):
                app_logger.error(f"[post_pr_value][{current_user}] Invalid value for PR")
                raise HTTPException(status_code=400, detail="Bad request")

            existing_value = session.exec(
                select(PRValue).where(PRValue.pr_id == pr_id, PRValue.cdate == parsed_date)
            ).first()
            if existing_value:
                raise HTTPException(status_code=409, detail="The resource already exists")

            new_pr_value = PRValue(value=value.value, cdate=parsed_date, pr=db_pr)
        except Exception as exc:
            app_logger.error(f"[post_pr_value][{current_user}] Exception during parsing: {exc}")
            raise HTTPException(
                status_code=500,
                detail="Roses are red, violets are blue, if you're reading this, I'm sorry for you",
            )

        session.add(new_pr_value)
        values.append(new_pr_value)

    session.commit()
    return [PRValueRead.serialize(v) for v in values]


@router.put("/{pr_id}/value/{value_id}", response_model=PRValueRead)
def put_pr_value(
    pr_id: int,
    value_id: int,
    value_data: PRValueCreateOrUpdate,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> PRValueRead:
    db_pr = session.get(PR, pr_id)
    verify_exists_and_owns(current_user, db_pr)

    db_pr_value = session.get(PRValue, value_id)
    if not db_pr_value:
        raise HTTPException(status_code=404, detail="The resource does not exist")

    if db_pr_value.pr_id != pr_id:
        app_logger.error(f"[put_pr_value][{current_user}] PR Value does not belong to the specified PR")
        raise HTTPException(status_code=400, detail="Bad request")

    if not PRValueCreateOrUpdate.value_matches_record_key(db_pr.key, value_data.value):
        app_logger.error(f"[put_pr_value][{current_user}] Invalid value for PR")
        raise HTTPException(status_code=400, detail="Bad request")

    value_data = value_data.model_dump(exclude_unset=True)

    # Ensure that cdate string is converted to date obj
    if "cdate" in value_data:
        parsed_date = parse_str_or_date_to_date(value_data["cdate"])
        existing_value = session.exec(
            select(PRValue).where(
                PRValue.pr_id == pr_id,
                PRValue.cdate == parsed_date,
                PRValue.id != value_id,
            )
        ).first()
        if existing_value:
            raise HTTPException(status_code=409, detail="The resource already exists")
        value_data["cdate"] = parsed_date

    for key, value in value_data.items():
        setattr(db_pr_value, key, value)

    session.add(db_pr_value)
    session.commit()
    session.refresh(db_pr_value)
    return PRValueRead.serialize(db_pr_value)


@router.delete("/{pr_id}/value/{value_id}")
def delete_pr_value(
    pr_id: int,
    value_id: int,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
) -> dict:
    db_pr = session.get(PR, pr_id)
    verify_exists_and_owns(current_user, db_pr)

    db_pr_value = session.get(PRValue, value_id)
    if not db_pr_value:
        raise HTTPException(status_code=404, detail="The resource does not exist")

    if db_pr_value.pr_id != pr_id:
        raise HTTPException(status_code=400, detail="Bad request")

    session.delete(db_pr_value)
    session.commit()
    return {}
