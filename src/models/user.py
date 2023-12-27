import typing

from pydantic import AnyUrl, BaseModel, EmailStr

from core.config import Settings, get_settings

settings: Settings = get_settings()


class CreateUser(BaseModel):
    connection: str = settings.AUTH0_DEFAULT_DB_CONNECTION
    email: EmailStr
    password: str
    name: str
    verify_email: bool = True
    email_verified: typing.Optional[bool] = False
    given_name: typing.Optional[str] = None
    family_name: typing.Optional[str] = None
    nickname: typing.Optional[str] = None
    picture: typing.Optional[AnyUrl] = None
