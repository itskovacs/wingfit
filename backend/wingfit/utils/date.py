from datetime import UTC, date, datetime, timedelta

from fastapi import HTTPException


def dt_utc_str() -> str:
    return datetime.now(UTC).isoformat()


def dt_utc() -> date:
    return datetime.now(UTC)


def dt_utc_offset(min: int) -> date:
    return datetime.now(UTC) + timedelta(minutes=min)


def parse_str_or_date_to_date(cdate: str | date) -> date:
    if isinstance(cdate, str):
        try:
            return date.fromisoformat(cdate)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format, use YYYY-MM-DD")
    return cdate
