from fastapi.security import OAuth2PasswordBearer

from core.config import get_settings

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX[1:]}/auth/login")
