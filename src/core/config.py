from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Settings for the FastAPI server.
    Based on pydantic BaseSettings - powerful tool autoload the .env file in the background.
    """

    app_name: str = "mrv-service"
    root_path: str = ""
    ENV: str = "local"
    HOST: str = "0.0.0.0"
    PORT: int = 80
    RELOAD: bool = True
    CLIENT_ORIGIN_URLS: str = "http://localhost:3000,https://app.mealhow.ai"
    API_V1_PREFIX: str = "/api/v1"
    LOGGING_LEVEL: str = "CRITICAL"
    WHITELISTED_PATHS: set[str] = {
        "/docs",
        "/status",
        "/error",
        "/openapi.json",
    }

    # Custom headers
    CLIENT_COUNTRY_HEADER: str = "X-Client-Country"
    CLIENT_COUNTRY_SUBDIVISION_HEADER: str = "X-Client-Country-Subdivision"
    CLIENT_CDN_CACHE_ID_HEADER: str = "X-Client-Cdn-Cache-Id"
    CLIENT_PROTOCOL_HEADER: str = "X-Client-Protocol"
    CLIENT_LAT_LONG_HEADER: str = "X-Client-Lat-Long"

    # Elastic APM configuration
    ELASTIC_APM_SERVER_URL: str = ""
    ELASTIC_APM_ENABLED: bool = False
    ELASTIC_APM_LOG_LEVEL: str = "INFO"
    ELASTIC_APM_ENVIRONMENT: str = "dev?"
    ELASTIC_APM_DEBUG: bool = False
    ELASTIC_APM_CAPTURE_BODY: str = "all"

    # Auth0 configuration
    AUTH0_DOMAIN: str
    AUTH0_ALGORITHMS: str = "RS256"
    AUTH0_DEFAULT_DB_CONNECTION: str
    AUTH0_API_DEFAULT_AUDIENCE: str
    AUTH0_APPLICATION_CLIENT_ID: str
    AUTH0_APPLICATION_CLIENT_SECRET: str
    AUTH0_TEST_USERNAME: str
    AUTH0_TEST_PASSWORD: str
    AUTH0_CALLBACK_URL: str = "http://localhost/login/callback"

    # Auth0 Management API
    AUTH0_MANAGEMENT_API_CLIENT_ID: str
    AUTH0_MANAGEMENT_API_CLIENT_SECRET: str
    AUTH0_MANAGEMENT_API_AUDIENCE: str

    # Google Cloud
    GCLOUD_SERVICE_ACCOUNT: str = "../sa.json"
    PROJECT_ID: str
    DATASTORE_DB: str
    GCS_MEAL_IMAGES_BUCKET: str | None = None
    PUBSUB_MEAL_PLAN_EVENT_TOPIC: str | None = None

    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_GPT_MODEL_VERSION: str

    # Mailgun
    MAILGUN_API_KEY: str | None = None
    MAILGUN_BASE_API_URL: str = "https://api.mailgun.net/v3/newsletter.mealhow.ai"

    # Stripe
    STRIPE_API_KEY: str
    STRIPE_WEBHOOK_SECRET: str | None = None

    class Config:
        """
        Tell BaseSettings the env file path
        """

        env_file = "../.env"


@lru_cache()
def get_settings(**kwargs: dict) -> Settings:
    """
    Get settings. ready for FastAPI's Depends.
    lru_cache - cache the Settings object per arguments given.
    """
    return Settings(**kwargs)
