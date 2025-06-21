from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from ..config import settings
from ..models.models import BlocCategory

_engine = None


def get_engine():
    global _engine
    if not _engine:
        _engine = create_engine(
            f"sqlite:///{settings.SQLITE_FILE}",
            connect_args={"check_same_thread": False},
        )
    return _engine


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db():
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def init_user_data(session: Session, username: str):
    categories = [
        {"user": username, "name": "note", "color": "#909090", "weight": 1},
        {"user": username, "name": "(p)rehab", "color": "#18a773", "weight": 2},
        {"user": username, "name": "weightlifting", "color": "#9d2a24", "weight": 3},
        {"user": username, "name": "gym", "color": "#e75480", "weight": 4},
        {"user": username, "name": "metcon", "color": "#3c74c4", "weight": 5},
        {"user": username, "name": "cardio", "color": "#6e4c23", "weight": 6},
        {"user": username, "name": "accessory", "color": "#c88a89", "weight": 7},
        {"user": username, "name": "other", "color": "#4c495c", "weight": 8},
    ]

    session.add_all([BlocCategory(**c) for c in categories])
    session.commit()
