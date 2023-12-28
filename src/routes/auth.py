from auth0.v3 import management
from auth0.v3.exceptions import Auth0Error
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.security import OAuth2PasswordRequestForm

from core.config import get_settings, Settings
from core.dependencies import (
    authentication,
    get_auth0_management_client,
    get_auth0_token_client,
)
from schemas.user import CreateUser

router = APIRouter()

settings: Settings = get_settings()


@router.post("/login")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth0_token: authentication.GetToken = Depends(get_auth0_token_client),
) -> dict:
    """
    Get access token from auth0 /oauth/token endpoint.
    """
    try:
        response = auth0_token.login(
            client_id=form_data.client_id or settings.AUTH0_APPLICATION_CLIENT_ID,
            client_secret=None,
            username=form_data.username,
            password=form_data.password,
            audience=settings.AUTH0_API_DEFAULT_AUDIENCE,
            scope="openid profile email",
            realm=None,
            grant_type="password",
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return {"access_token": response["access_token"], "token_type": "bearer"}


@router.get("/callback")
async def login_callback(
    code: str,
    auth0_token: authentication.GetToken = Depends(get_auth0_token_client),
) -> Response:
    try:
        response = auth0_token.authorization_code(
            grant_type="authorization_code",
            client_id=settings.AUTH0_APPLICATION_CLIENT_ID,
            client_secret=settings.AUTH0_APPLICATION_CLIENT_SECRET,
            code=code,
            redirect_uri="http://localhost/login/callback",
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return response


@router.post("/signup")
async def create_new_user(
    create_user: CreateUser,
    auth0_mgmt_client: management.Auth0 = Depends(get_auth0_management_client),
    auth0_token: authentication.GetToken = Depends(get_auth0_token_client),
) -> dict:
    """
    Create user in auth0.
    if verify_email=True -> send verification mail
    """
    try:
        # Create user in auth0 db
        auth0_mgmt_client.users.create(body=create_user.model_dump())

        # Get access token for new user
        response = auth0_token.login(
            client_id=settings.AUTH0_APPLICATION_CLIENT_ID,
            client_secret=settings.AUTH0_APPLICATION_CLIENT_SECRET,
            username=create_user.email,
            password=create_user.password,
            audience=settings.AUTH0_API_DEFAULT_AUDIENCE,
            scope="openid profile email",
            grant_type="password",
            realm=settings.AUTH0_DEFAULT_DB_CONNECTION,
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return {"access_token": response["access_token"], "token_type": "bearer"}
