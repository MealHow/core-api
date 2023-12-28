import typing

from pydantic import BaseModel, EmailStr

from core.config import get_settings, Settings

settings: Settings = get_settings()


class LoginUser(BaseModel):
    email: EmailStr
    password: str


class CreateUser(BaseModel):
    connection: str = settings.AUTH0_DEFAULT_DB_CONNECTION
    email: EmailStr
    password: str
    name: str
    verify_email: bool = True
    email_verified: typing.Optional[bool] = False
    nickname: typing.Optional[str] = None
