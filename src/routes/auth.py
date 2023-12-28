import stripe
from auth0.authentication import GetToken
from auth0.exceptions import Auth0Error
from auth0.management import Auth0
from fastapi import APIRouter, Depends, HTTPException, Response

from core.config import get_settings, Settings
from core.dependencies import get_auth0_management_client, get_auth0_token_client
from schemas.user import CreateUser, LoginUser

router = APIRouter()

settings: Settings = get_settings()


@router.post("/login")
async def login_for_access_token(
    data: LoginUser,
    auth0_token: GetToken = Depends(get_auth0_token_client),
) -> dict:
    """
    Get access token from auth0 /oauth/token endpoint.
    """
    try:
        response = await auth0_token.login_async(
            username=data.email,
            password=data.password,
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
    auth0_token: GetToken = Depends(get_auth0_token_client),
) -> Response:
    try:
        response = await auth0_token.authorization_code_async(
            grant_type="authorization_code",
            code=code,
            redirect_uri="http://localhost/login/callback",
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return response


@router.post("/signup")
async def create_new_user(
    create_user: CreateUser,
    auth0_mgmt_client: Auth0 = Depends(get_auth0_management_client),
    auth0_token: GetToken = Depends(get_auth0_token_client),
) -> dict:
    """
    Create user in auth0.
    if verify_email=True -> send verification mail
    """
    try:
        # Create user in auth0 db
        create_user.nickname = create_user.email
        await auth0_mgmt_client.users.create_async(body=create_user.model_dump())

        # Get access token for new user
        response = await auth0_token.login_async(
            username=create_user.email,
            password=create_user.password,
            audience=settings.AUTH0_API_DEFAULT_AUDIENCE,
            scope="openid profile email",
            grant_type="password",
            realm=settings.AUTH0_DEFAULT_DB_CONNECTION,
        )

        customer = stripe.Customer.create(email=create_user.email, name=create_user.name)
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)

    return {"access_token": response["access_token"], "token_type": "bearer", "stripe_customer_id": customer["id"]}
