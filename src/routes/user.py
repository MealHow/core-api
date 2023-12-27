import typing

from auth0.v3.exceptions import Auth0Error
from fastapi import APIRouter, Depends, HTTPException
from pydantic import AnyUrl, BaseModel, EmailStr

from src.core.config import Settings, get_settings
from src.core.dependencies import authentication, get_auth0_management_client, get_auth0_users_client, management
from src.security.funcs import verify_token

router = APIRouter()

settings: Settings = get_settings()


@router.get("/me")
async def read_user_me(
    access_token: str = Depends(verify_token), auth0_users: authentication.Users = Depends(get_auth0_users_client)
) -> dict:
    try:
        userinfo = auth0_users.userinfo(access_token=access_token)
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    return userinfo


class CreateUser(BaseModel):
    connection: str = settings.AUTH0_DEFAULT_DB_CONNECTION
    email: EmailStr
    password: str
    name: str
    verify_email: bool = False  # Whether the user will receive a verification email after creation (true) or no email (false). Overrides behavior of email_verified parameter.
    email_verified: typing.Optional[
        bool
    ] = False  # Whether this email address is verified (true) or unverified (false). User will receive a verification email after creation if email_verified is false or not specified
    given_name: typing.Optional[str] = None
    family_name: typing.Optional[str] = None
    nickname: typing.Optional[str] = None
    picture: typing.Optional[AnyUrl] = None


@router.post("/")
async def create_new_user(
    create_user: CreateUser, auth0_mgmt_client: management.Auth0 = Depends(get_auth0_management_client)
):
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
