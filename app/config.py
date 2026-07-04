from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str = "super-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    GEMINI_API_KEY: str = ""
    GEMINI_TEXT_MODEL: str = "gemini-1.5-flash"
    GEMINI_VISION_MODEL: str = "gemini-1.5-flash"

    DATABASE_URL: str = "sqlite:///./data/pbl_smarthub.db"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
