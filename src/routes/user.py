import asyncio

from auth0.authentication import Users
from auth0.exceptions import Auth0Error
from auth0.management import Auth0
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import JSONResponse

from core.config import get_settings, Settings
from core.dependencies import (
    create_ndb_context,
    get_auth0_management_client,
    get_auth0_users_client,
)
from schemas.user import (
    Auth0AccountInfo,
    NewUserPassword,
    PatchPersonalInfo,
    PersonalInfo,
    Profile,
)
from services.user import get_user_personal_info_from_db, update_user_personal_info

router = APIRouter()

settings: Settings = get_settings()


@router.get("/profile", dependencies=[Depends(create_ndb_context)], response_model=Profile)
async def get_profile_info(
    request: Request, auth0_users: Users = Depends(get_auth0_users_client)
) -> JSONResponse | Profile:
    try:
        async with asyncio.TaskGroup() as group:
            auth0_account = group.create_task(auth0_users.userinfo_async(access_token=request.state.access_token))
            personal_info = group.create_task(get_user_personal_info_from_db(request.state.user_id))

        personal_info = personal_info.result()
        if not personal_info:
            return JSONResponse({"message": "No user found"}, status_code=404)

        return Profile(
            auth0_account=Auth0AccountInfo(**auth0_account.result()),
            personal_info=PersonalInfo(**personal_info),
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.patch("/profile", dependencies=[Depends(create_ndb_context)], response_model=PersonalInfo)
async def patch_user_personal_info(request: Request, personal_info: PatchPersonalInfo) -> JSONResponse | PersonalInfo:
    updated_personal_info = personal_info.model_dump(exclude_unset=True)
    personal_info = await update_user_personal_info(request.state.user_id, updated_personal_info)
    if not personal_info:
        return JSONResponse({"message": "No user found"}, status_code=404)

    return PersonalInfo(**personal_info)


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
