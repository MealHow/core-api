from auth0.authentication import Users
from auth0.exceptions import Auth0Error
from auth0.management import Auth0
from fastapi import APIRouter, Depends, HTTPException, Request

from core.config import get_settings, Settings
from core.dependencies import get_auth0_management_client, get_auth0_users_client
from schemas.user import NewUserPassword

router = APIRouter()

settings: Settings = get_settings()


@router.get("/profile")
async def get_profile_info(request: Request, auth0_users: Users = Depends(get_auth0_users_client)) -> dict:
    try:
        return await auth0_users.userinfo_async(access_token=request.state.access_token)
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.put("/password")
async def update_user_password(
    request: Request,
    new_password: NewUserPassword,
    auth0_mgmt_client: Auth0 = Depends(get_auth0_management_client),
) -> dict:
    try:
        return await auth0_mgmt_client.users.update_async(id=request.state.user_id, body=new_password.model_dump())
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post("/password/reset")
async def send_reset_password_link_to_email(
    request: Request,
    auth0_users: Users = Depends(get_auth0_users_client),
    auth0_mgmt_client: Auth0 = Depends(get_auth0_management_client),
) -> dict:
    # TODO: fix this
    try:
        user_info = await auth0_users.userinfo_async(access_token=request.state.access_token)
        return await auth0_mgmt_client.tickets.create_pswd_change_async(
            body={
                "result_url": "https://app.mealhow.ai/",
                "user_id": request.state.user_id,
                "client_id": settings.AUTH0_APPLICATION_CLIENT_ID,
                "connection_id": settings.AUTH0_DEFAULT_DB_CONNECTION,
                "email": user_info["email"],
                "ttl_sec": 0,
                "mark_email_as_verified": False,
                "includeEmailInRedirect": True,
            }
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
