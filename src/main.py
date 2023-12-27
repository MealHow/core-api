from typing import Callable, Literal

import secure
from elasticapm.contrib.starlette import ElasticAPM, make_apm_client
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.cloud import datastore, pubsub_v1
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.config import Settings, get_settings
from src.core.http_client import HttpClient
from src.core.logger import get_logger
from src.external_api.cloud_storage import CloudStorage
from src.helpers import custom_generate_unique_id
from src.routes import meal, meal_plan, shopping_list, subscription, token, user

settings: Settings = get_settings()
logger = get_logger(__name__)


http_client = HttpClient()
cloud_storage_session = CloudStorage()
pubsub_publisher = pubsub_v1.PublisherClient()
datastore_client = datastore.Client(database=settings.DATASTORE_DB)
app = FastAPI(root_path=settings.root_path, generate_unique_id_function=custom_generate_unique_id)

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
    allow_origins=settings.client_origin_urls.split(","),
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
    cloud_storage_session.initialise(http_client())


@app.on_event("shutdown")
async def shutdown() -> None:
    await http_client.stop()


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    message = str(exc.detail)

    return JSONResponse({"message": message}, status_code=exc.status_code)


@app.middleware("http")
async def set_secure_headers(request, call_next):
    response = await call_next(request)
    secure_headers.framework.fastapi(response)
    return response


@app.middleware("http")
async def client_middleware(request: Request, call_next: Callable) -> Response:
    request.state.gcloud_storage_client = cloud_storage_session
    request.state.datastore_client = datastore_client
    request.state.http_client_session = http_client
    request.state.pubsub_publisher = pubsub_publisher
    return await call_next(request)


@app.get("/status", status_code=status.HTTP_200_OK, operation_id="status_200")
async def get_status(request: Request) -> dict[str, Literal[True]]:
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
    token.router,
    prefix="/token",
    tags=["Token"],
)
app.include_router(
    user.router,
    prefix="/user",
    tags=["Users"],
)
app.include_router(
    meal.router,
    prefix="/meal",
    tags=["Meal"],
)
app.include_router(
    meal_plan.router,
    prefix="/meal-plan",
    tags=["Meal plan"],
)
app.include_router(
    subscription.router,
    prefix="/subscription",
    tags=["Subscription"],
)
app.include_router(
    shopping_list.router,
    prefix="/shopping-list",
    tags=["Shopping list"],
)

if __name__ == "__main__":
    import uvicorn

    if __name__ == "__main__":
        uvicorn.run(
            app,
            host=settings.host,
            port=settings.port,
            reload=settings.reload,
            server_header=False,
        )
