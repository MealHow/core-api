from auth0.authentication import Users
from auth0.exceptions import Auth0Error
from fastapi import APIRouter, Depends, HTTPException, Request

from core.config import get_settings, Settings
from core.dependencies import get_auth0_users_client

router = APIRouter()

settings: Settings = get_settings()


@router.get("/profile")
async def get_profile_info(request: Request, auth0_users: Users = Depends(get_auth0_users_client)) -> dict:
    try:
        return await auth0_users.userinfo_async(access_token=request.state.access_token)
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
