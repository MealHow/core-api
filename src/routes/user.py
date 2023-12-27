from auth0.v3 import authentication
from auth0.v3.exceptions import Auth0Error
from fastapi import APIRouter, Depends, HTTPException, Response

from core.config import get_settings, Settings
from core.dependencies import get_auth0_users_client
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
