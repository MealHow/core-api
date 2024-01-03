from typing import AsyncGenerator

from auth0 import authentication, management
from auth0.asyncify import asyncify

from core.clients import ndb_client
from core.config import get_settings, Settings
from core.http_client import http_client

settings: Settings = get_settings()


def get_auth0_token_client(management_client: bool = False) -> authentication.GetToken:
    """
    Return instance of GetToken.
    """
    get_token_class_wrapper = asyncify(authentication.GetToken)
    get_token = get_token_class_wrapper(
        domain=settings.AUTH0_DOMAIN,
        client_id=settings.AUTH0_MANAGEMENT_API_CLIENT_ID
        if management_client
        else settings.AUTH0_APPLICATION_CLIENT_ID,
        client_secret=settings.AUTH0_MANAGEMENT_API_CLIENT_SECRET
        if management_client
        else settings.AUTH0_APPLICATION_CLIENT_SECRET,
    )

    get_token.set_session(http_client())
    return get_token


def get_auth0_users_client() -> authentication.Users:
    """
    Return instance of GetToken.
    """
    users_class_wrapper = asyncify(authentication.Users)
    users = users_class_wrapper(settings.AUTH0_DOMAIN)
    users.set_session(http_client())
    return users


async def get_auth0_management_api_token() -> str:
    auth0_token = get_auth0_token_client(management_client=True)
    response = await auth0_token.client_credentials_async(
        audience=settings.AUTH0_MANAGEMENT_API_AUDIENCE,
    )
    return response["access_token"]


async def get_auth0_management_client() -> management.Auth0:
    """
    Return instance of Auth0 management API.
    """
    return management.Auth0(
        domain=settings.AUTH0_DOMAIN,
        token=await get_auth0_management_api_token(),
    )


async def get_auth0_database_client() -> authentication.Database:
    return authentication.Database(
        domain=settings.AUTH0_DOMAIN,
        client_id=settings.AUTH0_APPLICATION_CLIENT_ID,
        client_secret=settings.AUTH0_APPLICATION_CLIENT_SECRET,
    )


async def create_ndb_context() -> AsyncGenerator:
    with ndb_client.context():
        yield
