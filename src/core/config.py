from functools import lru_cache

from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Settings for the FastAPI server.
    Based on pydantic BaseSettings - powerful tool autoload the .env file in the background.
    """

    app_name: str = "mrv-service"
    env: str = "local"
    root_path: str = ""
    client_origin_urls: str = "http://localhost:3000,https://app.mealhow.ai"
    LOGGING_LEVEL: str = "CRITICAL"

    # Elastic APM configuration
    ELASTIC_APM_SERVER_URL: str = ""
    ELASTIC_APM_ENABLED: bool = False
    ELASTIC_APM_LOG_LEVEL: str = "INFO"
    ELASTIC_APM_ENVIRONMENT: str = "dev?"
    ELASTIC_APM_DEBUG: bool = False
    ELASTIC_APM_CAPTURE_BODY: str = "all"

    # AUTH0 configuration
    AUTH0_DOMAIN: str
    AUTH0_ALGORITHMS: str = "RS256"
    AUTH0_DEFAULT_DB_CONNECTION: str
    AUTH0_API_DEFAULT_AUDIENCE: str
    AUTH0_APPLICATION_CLIENT_ID: str
    AUTH0_APPLICATION_CLIENT_SECRET: str
    AUTH0_TEST_USERNAME: str
    AUTH0_TEST_PASSWORD: str

    # Management API
    AUTH0_MANAGEMENT_API_CLIENT_ID: str
    AUTH0_MANAGEMENT_API_CLIENT_SECRET: str
    AUTH0_MANAGEMENT_API_AUDIENCE: str

    # Google Cloud
    GCLOUD_SERVICE_ACCOUNT: str = "sa.json"

    class Config:
        """
        Tell BaseSettings the env file path
        """

        env_file = ".env"


@lru_cache()
def get_settings(**kwargs) -> Settings:
    """
    Get settings. ready for FastAPI's Depends.
    lru_cache - cache the Settings object per arguments given.
    """
    settings = Settings(**kwargs)
    return settings
