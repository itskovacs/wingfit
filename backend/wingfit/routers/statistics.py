import csv
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import extract
from sqlmodel import func, select

from ..deps import SessionDep, get_current_username
from ..models.models import Bloc, BlocCategory, BlocRead, HealthWatchData, HealthWatchDataRead
from ..utils.date import parse_str_or_date_to_date
from ..utils.file import download_file, upload_f_to_tempfile
from ..utils.logging import app_logger
from ..utils.watchparsers import applewatch_normalize, mywhoop_normalize

router = APIRouter(prefix="/api/stats", tags=["statistics"])


@router.get("/notes", response_model=list[BlocRead])
def get_blocs_note(session: SessionDep, current_user: Annotated[str, Depends(get_current_username)]) -> list:
    category = session.exec(
        select(BlocCategory)
        .where(BlocCategory.user == current_user)
        .where(BlocCategory.name == "note")
        .options(selectinload(BlocCategory.blocs))
    ).one_or_none()

    if not category:
        return []

    return [BlocRead.serialize(c) for c in category.blocs]


@router.get("/weekday_duration")
def get_weekday_duration_per_week(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    year: str | int | None = None,
):
    year = int(year) if year else datetime.now().year

    query = (
        select(
            extract("dow", Bloc.cdate).label("weekday"),
            extract("week", Bloc.cdate).label("week"),
            extract("month", Bloc.cdate).label("month"),
            extract("year", Bloc.cdate).label("year"),
            func.sum(Bloc.duration).label("duration"),
        )
        .where(Bloc.user == current_user)
        .where(Bloc.duration.isnot(None))
        .where(extract("year", Bloc.cdate) == year)
        .group_by("year", "month", "week", "weekday")
    )

    results = session.exec(query).all()

    month_data = {}  # { month: { week: [0,0,0,0,0,0,0] } }
    for row in results:
        month = int(row.month)
        week = int(row.week)
        # Map dow to isodow (Mon = 0, Sun = 6)
        idx = int(row.weekday) - 1 if int(row.weekday) != 0 else 6
        month_data.setdefault(month, {}).setdefault(week, [0] * 7)[idx] = row.duration or 0

    out = {}  # { month: [ [week1], [week2], ... ] }
    for month, week_map in month_data.items():
        weeks_sorted = [week_map[week] for week in sorted(week_map)]
        out[month] = weeks_sorted

    return out


@router.get("/week_duration")
def get_category_duration_per_week(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    year: str | int | None = None,
) -> list:
    year = int(year) if year else datetime.now().year

    query = (
        select(
            extract("week", Bloc.cdate).label("week"),
            extract("year", Bloc.cdate).label("year"),
            BlocCategory.name.label("category"),
            func.sum(Bloc.duration).label("duration"),
            BlocCategory.color.label("color"),
            BlocCategory.weight.label("weight"),
        )
        .join(BlocCategory, Bloc.category_id == BlocCategory.id)
        .where(Bloc.user == current_user)
        .where(Bloc.duration.isnot(None))
        .where(extract("year", Bloc.cdate) == year)
        .group_by("year", "week", "category")
    )

    results = session.exec(query).all()

    category_data = {}

    for r in results:
        category_data.setdefault(
            r.category,
            {"color": r.color, "order": r.weight, "data": {w: 0 for w in range(0, 52)}},
        )

        category_data[r.category]["data"][r.week] = r.duration

    datasets = [
        {
            "label": category.upper(),
            "order": category_data[category]["order"],
            "backgroundColor": category_data[category]["color"],
            "data": [category_data[category]["data"][week] for week in range(0, 52)],
        }
        for category in category_data
    ]

    return datasets


@router.get("/healthwatch", response_model=list[HealthWatchDataRead])
def get_hw_data(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    year: str | int | None = None,
) -> list[HealthWatchDataRead]:
    year = int(year) if year else datetime.now().year

    query = (
        select(HealthWatchData)
        .where(HealthWatchData.user == current_user)
        .where(extract("year", HealthWatchData.cdate) == year)
        .order_by(HealthWatchData.cdate.asc())
    )

    results = session.exec(query).all()
    return [HealthWatchDataRead.serialize(r) for r in results]


@router.post("/applewatch_archive")
async def post_applewatch_archive(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    file: UploadFile = File(...),
):
    temporary_fp = await upload_f_to_tempfile(file)
    inserted = 0
    data = {}
    with open(temporary_fp, "r") as aw_data:
        content = aw_data.read()
        data = applewatch_normalize(content)

    existing_records = {
        record.cdate: record
        for record in session.exec(select(HealthWatchData).where(HealthWatchData.user == current_user)).all()
    }  # {date: HealthWatchData}

    for date, fields in data.items():
        date = parse_str_or_date_to_date(date)

        if date in existing_records:
            existing_record = existing_records[date]
            model_keys = HealthWatchData.model_fields.keys()

            for key, value in fields.items():
                if key in model_keys:
                    setattr(existing_record, key, value)

            session.add(existing_record)
            continue

        new_aw_data = HealthWatchData(cdate=date, user=current_user, **fields)
        session.add(new_aw_data)

    inserted = len(session.new)
    session.commit()
    Path(temporary_fp).unlink()

    return {"count": inserted}


@router.post("/whoop_archive")
async def post_whoop_archive(
    session: SessionDep,
    current_user: Annotated[str, Depends(get_current_username)],
    file: UploadFile | None = File(None),
    link: str | None = Form(None),
):
    if not file and not link:
        app_logger.error(f"[post_whoop_archive][{current_user}] No link / file provided")
        raise HTTPException(status_code=400, detail="Bad request")

    if link and not link.startswith("https://links.prod.whoop.com/"):
        app_logger.error(f"[post_whoop_archive][{current_user}] Whoop export URL looks incorrect")
        raise HTTPException(status_code=400, detail="Bad request")

    temporary_fp = ""
    if file:
        temporary_fp = await upload_f_to_tempfile(file)
    else:
        temporary_fp = await download_file(link)

    existing_records = {
        record.cdate: record
        for record in session.exec(select(HealthWatchData).where(HealthWatchData.user == current_user)).all()
    }  # {date: HealthWatchData}

    inserted = 0
    ext = file.filename.split(".")[-1]
    if link or ext == "zip":
        with zipfile.ZipFile(temporary_fp, "r") as whoop_archive:
            if "physiological_cycles.csv" not in whoop_archive.namelist():
                app_logger.error(
                    f"[post_whoop_archive][{current_user}] physiological_cycles.csv is missing in archive"
                )
                raise HTTPException(status_code=400, detail="Bad request")

            with whoop_archive.open("physiological_cycles.csv") as file:
                reader = csv.reader((line.decode("utf-8") for line in file), delimiter=",")
                next(reader)

                for row in reader:
                    if (
                        not row or not row[3] or not row[8]
                    ):  # Recovery or strain missing indicates the row is incomplete
                        continue

                    # Use 'awake' datetime because 'cycle' datetimes are gapped if you sleep late or miss a night, not the best solution but a quickwin
                    date_value = parse_str_or_date_to_date(row[13].split(" ")[0])
                    if date_value in existing_records:
                        existing_record = existing_records[date_value]

                        if existing_record.whoop_recovery != row[3]:
                            existing_record.whoop_recovery = row[3]
                            updated = True
                        if existing_record.hr_resting != row[4]:
                            existing_record.hr_resting = row[4]
                            updated = True
                        if existing_record.hrv != row[5]:
                            existing_record.hrv = row[5]
                            updated = True
                        if existing_record.whoop_strain != row[8]:
                            existing_record.whoop_strain = row[8]
                            updated = True
                        if existing_record.hr_max != row[10]:
                            existing_record.hr_max = row[10]
                            updated = True
                        if existing_record.hr_avg != row[11]:
                            existing_record.hr_avg = row[11]
                            updated = True
                        if existing_record.sleep_start != row[12]:
                            existing_record.sleep_start = row[12].split(" ")[1]
                            updated = True
                        if existing_record.sleep_end != row[13]:
                            existing_record.sleep_end = row[13].split(" ")[1]
                            updated = True
                        if existing_record.whoop_sleepscore != row[14]:
                            existing_record.whoop_sleepscore = row[14]
                            updated = True
                        if existing_record.sleep_asleep != row[16]:
                            existing_record.sleep_asleep = row[16]
                            updated = True
                        if existing_record.sleep_total != row[17]:
                            existing_record.sleep_total = row[17]
                            updated = True

                        if updated:
                            session.add(existing_record)
                        continue

                    new_whoop_data = HealthWatchData(
                        cdate=date_value,
                        user=current_user,
                        whoop_recovery=row[3],
                        hr_resting=row[4],
                        hrv=row[5],
                        whoop_strain=row[8],
                        hr_max=row[10],
                        hr_avg=row[11],
                        sleep_start=row[12].split(" ")[1],
                        sleep_end=row[13].split(" ")[1],
                        whoop_sleepscore=row[14],
                        sleep_asleep=row[16],
                        sleep_total=row[17],
                    )
                    session.add(new_whoop_data)

    elif ext == "json":  # MyWhoop parser
        data = {}
        with open(temporary_fp, "r") as w_data:
            content = w_data.read()
            data = mywhoop_normalize(content)

        for date, fields in data.items():
            date = parse_str_or_date_to_date(date)

            if date in existing_records:
                existing_record = existing_records[date]
                model_keys = HealthWatchData.model_fields.keys()

                for key, value in fields.items():
                    if key in model_keys:
                        setattr(existing_record, key, value)

                session.add(existing_record)
                continue

            new_w_data = HealthWatchData(cdate=date, user=current_user, **fields)
            session.add(new_w_data)

    inserted = len(session.new)
    session.commit()
    Path(temporary_fp).unlink()

    return {"count": inserted}
