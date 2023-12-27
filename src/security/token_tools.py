import logging
from typing import Optional

import httpx
from fastapi.security import SecurityScopes
from jose import jwt, JWTError

from core.config import get_settings
from core.custom_exceptions import CredentialsException, PermissionsException
from security.token import AccessToken

settings = get_settings()
JWKS = httpx.get(f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json").json()


class TokenTools:
    """Does all the access token authentication, authorization and parsing"""

    def __init__(self, token: str) -> None:
        self.token = token
        self.settings = get_settings()
        self.jwks = JWKS

    @property
    def header(self) -> dict:
        try:
            return jwt.get_unverified_header(self.token)
        except Exception as e:
            logging.error("Invalid token: %s", self.token)
            raise e

    @property
    def unverified_claim(self) -> AccessToken:
        claim = jwt.get_unverified_claims(self.token)
        return AccessToken(**claim)

    def verified_claim(self) -> AccessToken:
        """
        Try to decode the access token,
        return the decoded claim.
        """
        kid = self.header["kid"]
        for key in self.jwks["keys"]:
            if key["kid"] == kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
        try:
            verified_claim = jwt.decode(
                self.token,
                key=rsa_key,
                algorithms=[self.settings.AUTH0_ALGORITHMS],
                audience=self.settings.AUTH0_API_DEFAULT_AUDIENCE,
                issuer=f"https://{self.settings.AUTH0_DOMAIN}/",
            )

        except JWTError:
            raise CredentialsException()

        return AccessToken(**verified_claim)

    def verify(self, security_scopes: Optional[SecurityScopes] = None) -> bool:
        """
        Verify both access token and scopes (if given).
        Return True / False
        """
        verified_claim = self.verified_claim()
        if security_scopes:
            for scope in security_scopes.scopes:
                if scope not in verified_claim.permissions:
                    raise PermissionsException()
        return True

    def get_user_id(self, verify: bool = True) -> str:
        """
        Return the 'sub' argument from the access token.
        """
        if verify:
            return self.verified_claim().sub
        else:
            return self.unverified_claim.sub
