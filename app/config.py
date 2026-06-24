from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rankguard"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
