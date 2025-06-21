import re
import secrets
from datetime import UTC, date, datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, StringConstraints
from pydantic_settings import BaseSettings
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import MetaData


convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

SQLModel.metadata = MetaData(naming_convention=convention)


class Settings(BaseSettings):
    AUTH_METHOD: str = "local"  # "local" or "oidc"

    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_AUTH_URL: str = ""
    OIDC_TOKEN_URL: str = ""
    OIDC_USERINFO_URL: str = ""
    OIDC_REDIRECT_URI: str = ""

    ASSETS_FOLDER: str = "storage/assets"
    FRONTEND_FOLDER: str = "frontend"
    SQLITE_FILE: str = "storage/wingfit.sqlite"
    SECRET_KEY: str = secrets.token_hex(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 1440

    OPENAI_API_KEY: str = ""
    OPEN_AI_HOST: str = ""

    class Config:
        env_file = "storage/settings.yml"


class ResultKeyEnum(str, Enum):
    KG = "kg"
    REP = "rep"
    TIME = "time"


class LoginRegisterModel(BaseModel):
    username: Annotated[
        str,
        StringConstraints(min_length=1, max_length=19, pattern=r"^[a-zA-Z0-9_-]+$"),
    ]
    password: str


class AuthParamsOIDC(BaseModel):
    OIDC_HOST: str
    OIDC_CLIENT_ID: str
    OIDC_REALM: str
    OIDC_REDIRECT_URI: str


class AuthParams(BaseModel):
    auth: str
    oidc: AuthParamsOIDC | None
    register_enabled: bool


class Token(BaseModel):
    access_token: str
    refresh_token: str


class TokenData(BaseModel):
    username: str | None = None


class ImageBase(SQLModel):
    filename: str


class Image(ImageBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user: str = Field(foreign_key="user.username", ondelete="CASCADE")
    programs: list["Program"] | None = Relationship(back_populates="image")


class UpdateUserPassword(BaseModel):
    current: str
    new: str


class UserBase(SQLModel): ...


class User(UserBase, table=True):
    username: str = Field(primary_key=True)
    password: str
    is_active: bool = True
    is_su: bool = False
    last_connect: datetime | None = Field(default_factory=lambda: datetime.now(UTC))
    api_token: str | None = None
    mfa_enabled: bool = False
    mfa_secret: str | None = None


class UserRead(UserBase):
    username: str
    last_connect: datetime | None
    api_token: bool = False
    is_active: bool
    is_su: bool
    mfa_enabled: bool

    @classmethod
    def serialize(cls, obj: User) -> "UserRead":
        return cls(
            username=obj.username,
            last_connect=obj.last_connect,
            api_token=True if obj.api_token else False,
            is_active=obj.is_active,
            is_su=obj.is_su,
            mfa_enabled=obj.mfa_enabled,
        )


class StashBase(SQLModel):
    content: str


class Stash(StashBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cdate: date = Field(default_factory=lambda: datetime.now(UTC).date())
    user: str = Field(foreign_key="user.username", ondelete="CASCADE")


class StashRead(StashBase):
    id: int
    content: str
    cdate: date

    @classmethod
    def serialize(cls, obj: Stash) -> "StashRead":
        return cls(
            id=obj.id,
            content=obj.content,
            cdate=obj.cdate,
        )


class BlocCategoryBase(SQLModel):
    name: str
    color: str
    weight: int


class BlocCategory(BlocCategoryBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user: str = Field(foreign_key="user.username", ondelete="CASCADE")
    blocs: list["Bloc"] = Relationship(back_populates="category")
    programblocs: list["ProgramStepBloc"] = Relationship(back_populates="category")


class BlocCategoryCreate(BlocCategoryBase):
    name: str
    color: str
    weight: int | None


class BlocCategoryUpdate(BlocCategoryBase):
    name: str | None = None
    color: str | None = None
    weight: int | None = None


class BlocCategoryRead(BlocCategoryBase):
    id: int
    weight: int | None

    @classmethod
    def serialize(cls, obj: BlocCategory) -> "BlocCategoryRead":
        return cls(
            id=obj.id,
            name=obj.name,
            color=obj.color,
            weight=obj.weight,
        )


class BlocResultBase(SQLModel):
    value: str
    comment: str | None = None
    key: ResultKeyEnum


class BlocResult(BlocResultBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    bloc: "Bloc" = Relationship(back_populates="result")


class BlocResultRead(BlocResultBase):
    ...

    @classmethod
    def serialize(cls, obj: BlocResult) -> "BlocResultRead":
        return cls(id=obj.id, value=obj.value, comment=obj.comment, key=obj.key)


class BlocBase(SQLModel):
    content: str
    duration: int | None = None


class Bloc(BlocBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cdate: date = Field(default_factory=lambda: datetime.now(UTC).date())
    user: str = Field(foreign_key="user.username", ondelete="CASCADE")
    result_id: int | None = Field(default=None, foreign_key="blocresult.id")
    result: BlocResult | None = Relationship(back_populates="bloc")

    category_id: int = Field(foreign_key="bloccategory.id", ondelete="CASCADE")
    category: BlocCategory | None = Relationship(back_populates="blocs")


class BlocCreate(BlocBase):
    category: BlocCategoryRead | None = None
    category_id: int | None = None
    cdate: str | date = Field(default_factory=lambda: datetime.now(UTC).date())


class BlocUpdate(BlocBase):
    content: str | None = None
    category: BlocCategoryRead | None = None
    category_id: int | None = None
    result_id: int | None = None
    cdate: str | date = Field(default_factory=lambda: datetime.now(UTC).date())


class BlocRead(BlocBase):
    id: int | None
    cdate: date
    category: BlocCategoryRead
    result: BlocResultRead | None

    @classmethod
    def serialize(cls, obj: Bloc) -> "BlocRead":
        return cls(
            id=obj.id,
            duration=obj.duration,
            content=obj.content,
            cdate=obj.cdate,
            category=BlocCategoryRead.serialize(obj.category),
            result=BlocResultRead.serialize(obj.result) if obj.result else None,
        )


class PRBase(SQLModel):
    name: str
    key: ResultKeyEnum


class PR(PRBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    values: list["PRValue"] = Relationship(back_populates="pr", cascade_delete=True)
    user: str = Field(foreign_key="user.username", ondelete="CASCADE")


class PRCreate(PRBase):
    values: list["PRValueCreateOrUpdate"] | None = None
    name: str | None = None
    key: ResultKeyEnum | None = None


class PRUpdate(PRBase):
    name: str | None = None
    key: ResultKeyEnum | None = None


class PRRead(PRBase):
    id: int | None = Field(default=None, primary_key=True)
    values: list["PRValueRead"]

    @classmethod
    def serialize(cls, obj: PR) -> "PRRead":
        return cls(
            id=obj.id,
            name=obj.name,
            key=obj.key,
            values=[PRValueRead.serialize(value) for value in obj.values],
        )


class PRValueBase(SQLModel):
    value: str


class PRValueCreateOrUpdate(PRValueBase):
    cdate: str | date = Field(default_factory=lambda: datetime.now(UTC).date())

    @classmethod
    def value_matches_record_key(cls, key: ResultKeyEnum, value: str) -> bool:
        if key == "rep":  # rep must be a positive int
            return value.isdigit() and int(value) > 0

        elif key == "kg":  # kg must be a positive float
            try:
                test_float = float(value)
                return test_float > 0
            except ValueError:
                return False
        if key == "time":  # time must be "[hh:]mm:ss"
            return bool(re.fullmatch(r"^(?:(?:(\d{,3}):)?([0-5]?\d):)?([0-5]?\d)$", value))
        return False


class PRValue(PRValueBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cdate: date = Field(default_factory=lambda: datetime.now(UTC).date())

    pr_id: int = Field(foreign_key="pr.id", ondelete="CASCADE")
    pr: PR | None = Relationship(back_populates="values")


class PRValueRead(PRValueBase):
    id: int
    cdate: date

    @classmethod
    def serialize(cls, obj: PR) -> "PRValueRead":
        return cls(
            id=obj.id,
            cdate=obj.cdate,
            value=obj.value,
        )


class ProgramBase(SQLModel):
    name: str
    description: str | None = None


class Program(ProgramBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cdate: date = Field(default_factory=lambda: datetime.now(UTC).date())
    user: str = Field(foreign_key="user.username", ondelete="CASCADE")
    image_id: int | None = Field(default=None, foreign_key="image.id", ondelete="CASCADE")
    image: Image | None = Relationship(back_populates="programs")
    steps: list["ProgramStep"] = Relationship(back_populates="program", cascade_delete=True)


class ProgramCreate(ProgramBase):
    image: str | None = None
    image_id: int | None = None


class ProgramUpdate(ProgramBase):
    name: str | None = None
    image: str | None = None
    image_id: int | None = None


class ProgramRead(ProgramBase):
    id: int
    image_id: int | None
    image: str | None
    steps: list["ProgramStepRead"]
    cdate: date

    @classmethod
    def serialize(cls, obj: Program) -> "ProgramRead":
        return cls(
            id=obj.id,
            name=obj.name,
            description=obj.description,
            cdate=obj.cdate,
            image_id=obj.image_id,
            image=obj.image.filename if obj.image else None,
            steps=[ProgramStepRead.serialize(step) for step in obj.steps],
        )


class ProgramReadComplete(ProgramRead):
    steps: list["ProgramStepWithBlocsRead"]

    @classmethod
    def serialize(cls, obj: Program) -> "ProgramRead":
        return cls(
            id=obj.id,
            name=obj.name,
            description=obj.description,
            cdate=obj.cdate,
            image_id=obj.image_id,
            image=obj.image.filename if obj.image else None,
            steps=[ProgramStepWithBlocsRead.serialize(step) for step in obj.steps],
        )


class ProgramStepBase(SQLModel):
    name: str
    repeat: int = 0
    next_in: int = 1


class ProgramStep(ProgramStepBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cdate: date = Field(default_factory=lambda: datetime.now(UTC).date())
    user: str = Field(foreign_key="user.username", ondelete="CASCADE")
    program_id: int = Field(foreign_key="program.id", ondelete="CASCADE")
    program: Program | None = Relationship(back_populates="steps")

    blocs: list["ProgramStepBloc"] = Relationship(back_populates="program_steps", cascade_delete=True)


class ProgramStepUpdate(ProgramStepBase):
    name: str | None = None
    repeat: int | None = None
    next_in: int | None = None


class ProgramStepCreate(ProgramStepBase): ...


class ProgramStepWithBlocsRead(ProgramStepBase):
    id: int
    cdate: date
    blocs: list["ProgramStepBlocRead"]

    @classmethod
    def serialize(cls, obj: ProgramStep) -> "ProgramStepWithBlocsRead":
        return cls(
            id=obj.id,
            name=obj.name,
            cdate=obj.cdate,
            repeat=obj.repeat,
            blocs=[ProgramStepBlocRead.serialize(bloc) for bloc in obj.blocs],
        )


class ProgramStepRead(ProgramStepBase):
    id: int
    cdate: date
    blocs: list = []

    @classmethod
    def serialize(cls, obj: ProgramStep) -> "ProgramStepRead":
        return cls(id=obj.id, name=obj.name, cdate=obj.cdate, repeat=obj.repeat, blocs=[])


class ProgramStepBlocBase(SQLModel):
    content: str
    duration: int | None = None


class ProgramStepBloc(ProgramStepBlocBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    next_in: int
    user: str = Field(foreign_key="user.username", ondelete="CASCADE")

    category_id: int = Field(foreign_key="bloccategory.id", ondelete="CASCADE")
    category: BlocCategory | None = Relationship(back_populates="programblocs")

    program_step_id: int | None = Field(default=None, foreign_key="programstep.id", ondelete="CASCADE")
    program_steps: ProgramStep | None = Relationship(back_populates="blocs")


class ProgramStepBlocCreate(ProgramStepBlocBase):
    category: BlocCategoryRead | None = None
    category_id: int | None = None
    next_in: int = 1


class ProgramStepBlocUpdate(ProgramStepBlocBase):
    category: BlocCategoryRead | None = None
    category_id: int | None = None
    content: str | None = None
    next_in: int | None = None


class ProgramStepBlocRead(ProgramStepBlocBase):
    id: int
    next_in: int
    category: BlocCategoryRead

    @classmethod
    def serialize(cls, obj: ProgramStepBloc) -> "ProgramStepBlocRead":
        return cls(
            id=obj.id,
            content=obj.content,
            duration=obj.duration,
            category=BlocCategoryRead.serialize(obj.category),
            next_in=obj.next_in,
        )


class HealthWatchData(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    cdate: date = Field(index=True)
    user: str = Field(foreign_key="user.username", ondelete="CASCADE")

    steps: int | None
    stand_time: int | None
    hr_min: int | None
    hr_max: int | None
    hr_avg: int | None
    hr_resting: int | None
    hrv: int | None

    sleep_asleep: int | None
    sleep_start: str | None
    sleep_end: str | None
    sleep_total: int | None

    # Whoop specific
    whoop_recovery: int | None
    whoop_strain: float | None
    whoop_sleepscore: int | None


class HealthWatchDataRead(SQLModel):
    id: int
    cdate: date

    steps: int | None
    stand_time: int | None
    hr_min: int | None
    hr_max: int | None
    hr_avg: int | None
    hr_resting: int | None
    hrv: int | None

    sleep_asleep: int | None
    sleep_start: str | None
    sleep_end: str | None
    sleep_total: int | None

    # Whoop specific
    whoop_recovery: int | None
    whoop_strain: float | None
    whoop_sleepscore: int | None

    @classmethod
    def serialize(cls, obj: HealthWatchData) -> "HealthWatchDataRead":
        return cls(
            id=obj.id,
            cdate=obj.cdate,
            steps=obj.steps,
            stand_time=obj.stand_time,
            hr_min=obj.hr_min,
            hr_max=obj.hr_max,
            hr_avg=obj.hr_avg,
            hr_resting=obj.hr_resting,
            hrv=obj.hrv,
            sleep_asleep=obj.sleep_asleep,
            sleep_start=obj.sleep_start,
            sleep_end=obj.sleep_end,
            sleep_total=obj.sleep_total,
            whoop_recovery=obj.whoop_recovery,
            whoop_strain=obj.whoop_strain,
            whoop_sleepscore=obj.whoop_sleepscore,
        )
