from auth0.authentication import Database
from auth0.exceptions import Auth0Error
from auth0.management import Auth0
from fastapi import APIRouter, Depends, HTTPException, Request, status

from core import custom_exceptions
from core.config import get_settings, Settings
from core.dependencies import (
    create_ndb_context,
    get_auth0_database_client,
    get_auth0_management_client,
)
from schemas.exception import ExceptionResponse
from schemas.user import NewUserPassword, PatchPersonalInfo, PersonalInfo, Profile
from services.user import (
    create_reset_password_request,
    get_user_personal_info_from_db,
    update_user_personal_info,
)

router = APIRouter()

settings: Settings = get_settings()


@router.get(
    "/profile",
    status_code=status.HTTP_200_OK,
    response_model=Profile,
    responses={404: {"model": ExceptionResponse, "description": "User not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def get_profile_info(request: Request) -> Profile:
    response = await get_user_personal_info_from_db(request.state.user_id)
    if not response:
        raise custom_exceptions.NotFoundException("User not found")

    return Profile(
        email=response["email"],
        name=response["name"],
        personal_info=PersonalInfo(**response["personal_info"]),
    )


@router.patch(
    "/profile",
    status_code=status.HTTP_200_OK,
    response_model=Profile,
    responses={404: {"model": ExceptionResponse, "description": "User not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def patch_user_personal_info(request: Request, personal_info: PatchPersonalInfo) -> Profile:
    updated_personal_info = personal_info.model_dump(exclude_unset=True)
    personal_info = await update_user_personal_info(request.state.user_id, updated_personal_info)
    if not personal_info:
        raise custom_exceptions.NotFoundException("User not found")

    return Profile(**personal_info)


@router.put(
    "/password",
    status_code=status.HTTP_200_OK,
)
async def update_user_password(
    request: Request,
    new_password: NewUserPassword,
    auth0_mgmt_client: Auth0 = Depends(get_auth0_management_client),
) -> None:
    try:
        await auth0_mgmt_client.users.update_async(id=request.state.user_id, body=new_password.model_dump())
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


@router.post(
    "/password/reset",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(create_ndb_context)],
)
async def send_reset_password_link_to_email(
    request: Request,
    auth0_database_client: Database = Depends(get_auth0_database_client),
) -> None:
    await create_reset_password_request(request, auth0_database_client)
