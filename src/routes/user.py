from auth0.v3 import authentication, management
from auth0.v3.exceptions import Auth0Error
from fastapi import APIRouter, Depends, HTTPException, Response

from core.config import get_settings, Settings
from core.dependencies import get_auth0_management_client, get_auth0_users_client
from schemas.user import CreateUser
from security.funcs import verify_token

router = APIRouter()

settings: Settings = get_settings()


@router.get("/profile")
async def get_profile_info(
    access_token: str = Depends(verify_token), auth0_users: authentication.Users = Depends(get_auth0_users_client)
) -> Response:
    try:
        userinfo = auth0_users.userinfo(access_token=access_token)
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    return userinfo


@router.post("/sign-up")
async def create_new_user(
    create_user: CreateUser, auth0_mgmt_client: management.Auth0 = Depends(get_auth0_management_client)
) -> Response:
    """
    Create user in auth0.
    if verify_email=True -> send verification mail
    """
    # Create user in auth0 db
    try:
        response = auth0_mgmt_client.users.create(body=create_user.dict(exclude_none=True))
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    return response
