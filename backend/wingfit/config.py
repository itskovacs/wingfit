import secrets

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ASSETS_FOLDER: str = "storage/assets"
    FRONTEND_FOLDER: str = "frontend"
    SQLITE_FILE: str = "storage/wingfit.sqlite"
    LOG_FILE: str = "storage/wingfit.log"

    OPENAI_API_KEY: str = ""
    OPEN_AI_HOST: str = ""

    REGISTER_ENABLE: bool = True
    AUTH_METHOD: str = "local"
    SECRET_KEY: str = secrets.token_hex(32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 1440

    OIDC_CLIENT_ID: str = ""
    OIDC_CLIENT_SECRET: str = ""
    OIDC_HOST: str = ""
    OIDC_REALM: str = "master"
    OIDC_REDIRECT_URI: str = ""

    class Config:
        env_file = "storage/config.yml"


settings = Settings()
