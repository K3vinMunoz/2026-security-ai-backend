from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration.

    All environment access must go through this object instead of scattered
    ``os.getenv`` calls.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "security-ai-backend"
    app_version: str = "0.1.0"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "security_ai"
    postgres_user: str = "security_ai"
    postgres_password: str = "security_ai_dev_password"

    @property
    def sqlalchemy_database_url(self) -> str:
        """Async-capable DSN for SQLAlchemy 2 + psycopg 3.

        Derived from the individual POSTGRES_* variables so credentials stay in
        the environment instead of a single hardcoded connection string.
        ``postgresql+psycopg`` is the async driver pair for psycopg 3.
        """
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


settings = Settings()
