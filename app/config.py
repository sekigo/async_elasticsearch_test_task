from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5433/documents"
    es_url: str = "http://localhost:9200"
    es_index: str = "documents"
    search_limit: int = 20


settings = Settings()
