from typing import NamedTuple

import jwt
from starlette.requests import Request as StarletteRequest

from core.config import get_settings
from core.custom_exceptions import (
    BadCredentialsException,
    RequiresAuthenticationException,
    UnableCredentialsException,
)

settings = get_settings()


class AuthorizationHeaderElements(NamedTuple):
    authorization_scheme: str
    bearer_token: str
    are_valid: bool


def get_authorization_header_elements(
    authorization_header: str,
) -> AuthorizationHeaderElements:
    try:
        authorization_scheme, bearer_token = authorization_header.split()
    except ValueError:
        raise BadCredentialsException
    else:
        valid = authorization_scheme.lower() == "bearer" and bool(bearer_token.strip())
        return AuthorizationHeaderElements(authorization_scheme, bearer_token, valid)


def get_bearer_token(request: StarletteRequest) -> str:
    authorization_header = request.headers.get("Authorization")
    if authorization_header:
        authorization_header_elements = get_authorization_header_elements(authorization_header)
        if authorization_header_elements.are_valid:
            return authorization_header_elements.bearer_token
        else:
            raise BadCredentialsException
    else:
        raise RequiresAuthenticationException


def verify_jwt_token(jwt_access_token: str, jwks_client: jwt.PyJWKClient) -> dict:
    try:
        jwt_signing_key = jwks_client.get_signing_key_from_jwt(jwt_access_token).key
        return jwt.decode(
            jwt_access_token,
            jwt_signing_key,
            algorithms=settings.AUTH0_ALGORITHMS,
            audience=settings.AUTH0_API_DEFAULT_AUDIENCE,
            issuer=f"https://{settings.AUTH0_DOMAIN}/",
        )
    except jwt.exceptions.PyJWKClientError:
        raise UnableCredentialsException
    except jwt.exceptions.InvalidTokenError:
        raise BadCredentialsException
