from typing import Any, Callable, Literal

import jwt
import openai
import secure
from async_stripe import stripe
from elasticapm.contrib.starlette import ElasticAPM, make_apm_client
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from core.auth import get_bearer_token, verify_jwt_token
from core.clients import cloud_storage_session, ndb_client, pubsub_publisher
from core.config import get_settings, Settings
from core.custom_exceptions import (
    BadCredentialsException,
    RequiresAuthenticationException,
    UnableCredentialsException,
)
from core.helpers import custom_generate_unique_id
from core.http_client import http_client
from core.logger import get_logger
from routes import auth, meal, meal_plan, shopping_list, subscription, user

settings: Settings = get_settings()
logger = get_logger(__name__)

stripe.api_key = settings.STRIPE_API_KEY

jwks_client = jwt.PyJWKClient(f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json")
app = FastAPI(
    root_path=settings.root_path,
    generate_unique_id_function=custom_generate_unique_id,
    docs_url=None if settings.ENV == "prod" else "/docs",
    redoc_url=None if settings.ENV == "prod" else "/redoc",
    openapi_url=None if settings.ENV == "prod" else "/openapi.json",
)

csp = secure.ContentSecurityPolicy().default_src("'self'").frame_ancestors("'none'")
hsts = secure.StrictTransportSecurity().max_age(31536000).include_subdomains()
referrer = secure.ReferrerPolicy().no_referrer()
cache_value = secure.CacheControl().no_cache().no_store().max_age(0).must_revalidate()
x_frame_options = secure.XFrameOptions().deny()

secure_headers = secure.Secure(
    csp=csp,
    hsts=hsts,
    referrer=referrer,
    cache=cache_value,
    xfo=x_frame_options,
)

apm = make_apm_client(
    {
        "SERVICE_NAME": settings.app_name,
        "SERVER_URL": settings.ELASTIC_APM_SERVER_URL,
        "ENABLED": settings.ELASTIC_APM_ENABLED,
        "LOG_LEVEL": settings.ELASTIC_APM_LOG_LEVEL,
        "ENVIRONMENT": settings.ELASTIC_APM_ENVIRONMENT,
        "DEBUG": settings.ELASTIC_APM_DEBUG,
        "TRANSACTIONS_IGNORE_PATTERNS": [
            "/status",
        ],
        "CAPTURE_BODY": settings.ELASTIC_APM_CAPTURE_BODY,
    }
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CLIENT_ORIGIN_URLS.split(","),
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    max_age=86400,
)

# Elastic APM instrumentation needs to be added after all the BaseHTTPMiddlewares to mitigate the mutated
# context objects in Starlette
# Caveat: APM instrumentation will lose the span data of the upward middlewares in the stack
app.add_middleware(ElasticAPM, client=apm)


@app.on_event("startup")
async def startup() -> None:
    http_client.start()
    openai.aiosession.set(http_client())
    cloud_storage_session.initialise(http_client())


@app.on_event("shutdown")
async def shutdown() -> None:
    await http_client.stop()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: Any) -> JSONResponse:
    message = str(exc.detail)

    return JSONResponse({"message": message}, status_code=exc.status_code)


@app.middleware("http")
async def authorization_middleware(request: Request, call_next: Callable) -> Response | JSONResponse:
    if request.url.path in settings.WHITELISTED_PATHS or request.url.path.startswith(f"{settings.API_V1_PREFIX}/auth"):
        return await call_next(request)

    try:
        jwt_access_token = get_bearer_token(request)
        payload = verify_jwt_token(jwt_access_token, jwks_client)
    except (BadCredentialsException, RequiresAuthenticationException, UnableCredentialsException) as e:
        message = str(e.detail)
        return JSONResponse({"message": message}, status_code=e.status_code)

    request.state.access_token = jwt_access_token
    request.state.user_id = payload["sub"]

    return await call_next(request)


@app.middleware("http")
async def set_secure_headers(request: Request, call_next: Callable) -> Response:
    response = await call_next(request)

    if request.url.path in settings.WHITELISTED_PATHS:
        return response

    secure_headers.framework.fastapi(response)
    return response


@app.middleware("http")
async def client_middleware(request: Request, call_next: Callable) -> Response:
    request.state.gcloud_storage_client = cloud_storage_session
    request.state.ndb_client = ndb_client
    request.state.http_client_session = http_client
    request.state.pubsub_publisher = pubsub_publisher
    return await call_next(request)


@app.get("/status", status_code=status.HTTP_200_OK, operation_id="status_200")
async def get_status() -> dict[str, Literal[True]]:
    return {"healthy": True}


@app.get(
    "/error",
    status_code=status.HTTP_200_OK,
    description="""
    This endpoint is for generating 500s to be read by apm.
    All it does it return errors"
    """,
)
async def get_error() -> None:
    raise Exception


app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Auth"],
)
app.include_router(
    user.router,
    prefix=f"{settings.API_V1_PREFIX}/user",
    tags=["Users"],
)
app.include_router(
    meal.router,
    prefix=f"{settings.API_V1_PREFIX}/meals",
    tags=["Meals"],
)
app.include_router(
    meal_plan.router,
    prefix=f"{settings.API_V1_PREFIX}/meal-plans",
    tags=["Meal Plans"],
)
app.include_router(
    subscription.router,
    prefix=f"{settings.API_V1_PREFIX}/subscription",
    tags=["Subscription"],
)
app.include_router(
    shopping_list.router,
    prefix=f"{settings.API_V1_PREFIX}/shopping-lists",
    tags=["Shopping Lists"],
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
    )
