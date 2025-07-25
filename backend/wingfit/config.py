import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    FRONTEND_FOLDER: str = "frontend"
    SQLITE_FILE: str = "storage/wingfit.sqlite"

    ASSETS_FOLDER: str = "storage/assets"
    LOG_FILE: str = "storage/wingfit.log"
    SECRET_KEY: str = secrets.token_hex(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 1440

    REGISTER_ENABLE: bool = True
    OIDC_DISCOVERY_URL: str = ""
    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_REDIRECT_URI: str = ""

    class Config:
        env_file = "storage/config.yml"


settings = Settings()
