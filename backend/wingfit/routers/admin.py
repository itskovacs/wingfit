from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Body, File, Form, UploadFile, Depends, HTTPException
from sqlmodel import select

from .. import __version__
from ..db.core import init_user_data
from ..deps import SessionDep, get_current_username
from sqlalchemy.orm import selectinload
from ..models.models import (
    Bloc,
    BlocCategory,
    BlocCategoryRead,
    BlocRead,
    HealthWatchData,
    HealthWatchDataRead,
    Image,
    ResultKeyEnum,
    BlocResult,
    Program,
    PR,
    PRRead,
    PRValue,
    User,
    UserRead,
)
import json
from ..security import ensure_superuser, hash_password, verify_mfa_code
from ..utils.file import remove_image
from ..utils.date import parse_str_or_date_to_date
from ..utils.logging import app_logger
from .programs import export_program, import_program

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/users", response_model=list[UserRead])
async def admin_list_users(session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]):
    await ensure_superuser(session, current_user)

    users = session.exec(select(User)).all()
    return [UserRead.serialize(u) for u in users]


@router.put("/users/{username}/reset")
async def admin_reset_user_password(
    username: str,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    new: str = Body(..., embed=True),
    code: str = Body(..., embed=True),
):
    await ensure_superuser(session, current_user)

    db_user = session.get(User, current_user)
    if not db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Enable MFA to perform admin actions")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid code")

    target_user = session.get(User, username)
    if not target_user:
        raise HTTPException(status_code=404, detail="The resource does not exist")
    if target_user.is_su:
        raise HTTPException(status_code=403, detail="You cannot tamper an admin account")

    target_user.password = hash_password(new)
    session.add(target_user)
    session.commit()

    return {}


@router.put("/users/{username}/reset_mfa", response_model=UserRead)
async def admin_reset_mfa(
    username: str,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    code: str = Body(..., embed=True),
) -> UserRead:
    await ensure_superuser(session, current_user)

    db_user = session.get(User, current_user)
    if not db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Enable MFA to perform admin actions")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid code")

    target_user = session.get(User, username)
    if not target_user:
        raise HTTPException(status_code=404, detail="The resource does not exist")
    if target_user.is_su:
        raise HTTPException(status_code=403, detail="You cannot tamper an admin account")
    if not target_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Bad request")

    target_user.mfa_enabled = False
    target_user.mfa_secret = None
    session.add(target_user)
    session.commit()

    return UserRead.serialize(target_user)


@router.put("/import")
async def admin_import_data(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    file: UploadFile = File(...),
    code: str = Form(...),
):
    await ensure_superuser(session, current_user)

    db_user = session.get(User, current_user)
    if not db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Enable MFA to perform admin actions")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid code")

    if file.content_type != "application/json":
        raise HTTPException(status_code=415, detail="Resource format not supported")

    content = await file.read()
    data = json.loads(content)
    for user in data:
        if not session.get(User, user):
            app_logger.error(f"[admin_import_data] Trying to import data for unknown user {user}")
            continue

        d = data.get(user)
        for category in d.get("categories", []):
            category_exists = session.exec(
                select(BlocCategory).filter(
                    BlocCategory.user == user, BlocCategory.name == category.get("name")
                )
            ).first()
            if category_exists:
                continue

            new_category = BlocCategory(
                name=category.get("name"),
                color=category.get("color"),
                weight=category.get("weight"),
                user=user,
            )
            session.add(new_category)
        session.flush()

        for bloc in d.get("blocs", []):
            bloc_category_name = bloc.get("category", {}).get("name")
            category = session.exec(
                select(BlocCategory).filter(
                    BlocCategory.user == user, BlocCategory.name == bloc_category_name
                )
            ).first()
            if not category:
                app_logger.error(
                    f"[admin_import_data] Trying to import bloc for unknown category {bloc_category_name}"
                )
                continue

            new_bloc = Bloc(
                content=bloc.get("content"),
                duration=bloc.get("duration"),
                cdate=parse_str_or_date_to_date(bloc.get("cdate")),
                user=user,
            )
            new_bloc.category_id = category.id

            if bloc.get("result"):
                b = bloc.get("result")
                new_result = BlocResult(key=b.get("key"), value=b.get("value"), comment=b.get("comment"))
                session.add(new_result)
                new_bloc.result = new_result

            session.add(new_bloc)

        for program in d.get("programs", []):
            await import_program(session, user, program)

        for pr in d.get("pr", []):
            if pr.get("key") not in {item.value for item in ResultKeyEnum}:
                app_logger.error(f"[post_pr][{current_user}] Invalid key provided")
                raise HTTPException(status_code=400, detail="Bad request")

            new_pr = PR(name=pr.get("name"), key=pr.get("key"), user=user)

            if pr.get("values"):
                pr_values = []
                for value in pr.get("values"):
                    parsed_date = parse_str_or_date_to_date(value.get("cdate"))
                    pr_values.append(PRValue(value=value.get("value"), cdate=parsed_date, pr=new_pr))

                new_pr.values = pr_values

            session.add(new_pr)

        for hwdata in d.get("hw_data", []):
            existing_records = {
                record.cdate: record
                for record in session.exec(select(HealthWatchData).where(HealthWatchData.user == user)).all()
            }  # {date: HealthWatchData}

            date = parse_str_or_date_to_date(hwdata.get("cdate"))

            # We pop some keys because we unpack obj
            hwdata.pop("id", None)
            hwdata.pop("cdate", None)

            if int(d.get("_", {}).get("version", "0.0.0").split(".")[0]) < 5:
                # We need to normalize the previous model to the new
                hwdata["whoop_recovery"] = hwdata.get("recovery")
                hwdata.pop("recovery", None)
                hwdata["hr_resting"] = hwdata.get("resting_hr")
                hwdata.pop("resting_hr", None)
                hwdata["whoop_strain"] = hwdata.get("strain")
                hwdata.pop("strain", None)
                hwdata["whoop_sleepscore"] = hwdata.get("sleep_score")
                hwdata.pop("sleep_score", None)
                hwdata["sleep_total"] = hwdata.get("sleep_duration_awake", 0) + hwdata.get(
                    "sleep_duration_total", 0
                )
                hwdata.pop("sleep_duration_awake", None)
                hwdata.pop("sleep_duration_total", None)
                hwdata["sleep_duration_total"] = hwdata.get("sleep_asleep")
                hwdata.pop("sleep_asleep", None)

            if date in existing_records:
                existing_record = existing_records[date]
                model_keys = HealthWatchData.model_fields.keys()

                for key, value in hwdata.items():
                    if key in model_keys:
                        setattr(existing_record, key, value)

                session.add(existing_record)
                continue

            new_hw = HealthWatchData(**hwdata, cdate=date, user=user)
            session.add(new_hw)

    session.commit()
    return {}


@router.put("/export")
async def admin_export_data(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    code: str = Body(..., embed=True),
):
    await ensure_superuser(session, current_user)

    db_user = session.get(User, current_user)
    if not db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Enable MFA to perform admin actions")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid code")

    data = {}

    users = session.exec(select(User)).all()
    for user in users:
        username = user.username
        data[username] = {
            "_": {"at": datetime.timestamp(datetime.now()), "version": __version__},
            "categories": [
                BlocCategoryRead.serialize(c)
                for c in session.exec(select(BlocCategory).filter(BlocCategory.user == username))
            ],
            "pr": [
                PRRead.serialize(pr)
                for pr in session.exec(
                    select(PR).where(PR.user == username).options(selectinload(PR.values))
                )
            ],
            "blocs": [
                BlocRead.serialize(bloc) for bloc in session.exec(select(Bloc).filter(Bloc.user == username))
            ],
            "programs": [
                await export_program(program.id, session, username)
                for program in session.exec(select(Program).filter(Program.user == username))
            ],
        }

        hw_data = session.exec(
            select(HealthWatchData)
            .where(HealthWatchData.user == username)
            .order_by(HealthWatchData.cdate.desc())
        )
        data[username]["hw_data"] = [HealthWatchDataRead.serialize(r) for r in hw_data]

    return data


@router.put("/users/{username}/toggle_active", response_model=UserRead)
async def admin_toggle_user_active(
    username: str,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    code: str = Body(..., embed=True),
) -> UserRead:
    await ensure_superuser(session, current_user)

    db_user = session.get(User, current_user)
    if not db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Enable MFA to perform admin actions")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid code")

    target_user = session.get(User, username)
    if not target_user:
        raise HTTPException(status_code=404, detail="The resource does not exist")
    if target_user.is_su:
        raise HTTPException(status_code=403, detail="You cannot tamper an admin account")

    target_user.is_active = not target_user.is_active
    session.add(target_user)
    session.commit()
    session.refresh(target_user)

    return UserRead.serialize(target_user)


@router.put("/users/{username}/delete")
async def admin_delete_user(
    username: str,
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    code: str = Body(..., embed=True),
):
    await ensure_superuser(session, current_user)

    db_user = session.get(User, current_user)
    if not db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Enable MFA to perform admin actions")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid code")

    target_user = session.get(User, username)
    if not target_user:
        raise HTTPException(status_code=404, detail="The resource does not exist")
    if target_user.is_su:
        raise HTTPException(status_code=403, detail="You cannot tamper an admin account")

    # Retrieve fs images
    images = session.exec(select(Image).where(Image.user == username))
    images = [im.filename for im in images]

    session.delete(target_user)
    session.commit()

    # Delete the image files on fs
    for im in images:
        remove_image(im)

    return {}


@router.post("/users", response_model=UserRead)
async def admin_add_user(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    code: str = Body(..., embed=True),
    username: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
):
    await ensure_superuser(session, current_user)

    db_user = session.get(User, current_user)
    if not db_user.mfa_enabled:
        raise HTTPException(status_code=400, detail="Enable MFA to perform admin actions")

    success = verify_mfa_code(db_user.mfa_secret, code)
    if not success:
        raise HTTPException(status_code=403, detail="Invalid code")

    user = session.get(User, username)
    if user:
        raise HTTPException(status_code=409, detail="The resource already exists")

    new_user = User(username=username, password=hash_password(password))
    session.add(new_user)
    session.commit()

    init_user_data(session, new_user.username)

    return UserRead.serialize(new_user)
