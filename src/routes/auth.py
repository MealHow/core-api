from typing import Any

from auth0.authentication import GetToken
from auth0.management import Auth0
from fastapi import APIRouter, Depends, Request, status

from core.config import get_settings, Settings
from core.dependencies import (
    create_ndb_context,
    get_auth0_management_client,
    get_auth0_token_client,
)
from schemas.auth import AccessToken
from schemas.user import CreateUser, LoginUser
from services.auth import (
    create_user_in_db_and_auth0,
    get_access_token,
    get_callback_response,
)

router = APIRouter()

settings: Settings = get_settings()


@router.post(
    "/login",
    status_code=status.HTTP_200_OK,
    response_model=AccessToken,
)
async def login_for_access_token(
    data: LoginUser,
    auth0_token: GetToken = Depends(get_auth0_token_client),
) -> AccessToken:
    response = await get_access_token(auth0_token, data)
    return AccessToken(access_token=response["access_token"])


@router.get(
    "/callback",
    status_code=status.HTTP_200_OK,
)
async def login_callback(
    code: str,
    auth0_token: GetToken = Depends(get_auth0_token_client),
) -> dict[str, Any]:
    return await get_callback_response(auth0_token, code)


@router.post(
    "/signup",
    status_code=status.HTTP_201_CREATED,
    response_model=AccessToken,
    dependencies=[Depends(create_ndb_context)],
)
async def create_new_user(
    request: Request,
    create_user: CreateUser,
    auth0_mgmt_client: Auth0 = Depends(get_auth0_management_client),
    auth0_token: GetToken = Depends(get_auth0_token_client),
) -> AccessToken:
    response = await create_user_in_db_and_auth0(request, auth0_mgmt_client, auth0_token, create_user)
    return AccessToken(access_token=response["access_token"])
