from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SECRET_KEY: str = "super-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    GEMINI_API_KEY: str = ""
    GEMINI_TEXT_MODEL: str = "gemini-1.5-flash"
    GEMINI_VISION_MODEL: str = "gemini-1.5-flash"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_IMAGE_MODEL: str = "google/gemini-2.5-flash-image"
    IMAGE_GEN_LIMIT_PER_GROUP: int = 5

    GOOGLE_MAPS_API_KEY: str = ""

    DATABASE_URL: str = "postgresql+psycopg2://pbluser:pblpassword@db:5432/pbl_smarthub"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
