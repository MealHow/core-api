import typing
from enum import Enum

from pydantic import BaseModel, EmailStr

from core.config import get_settings, Settings

settings: Settings = get_settings()


class BiologicalSex(str, Enum):
    male = "male"
    female = "female"


class MeasurementSystem(str, Enum):
    imperial = "imperial"
    metric = "metric"


class LoginUser(BaseModel):
    email: EmailStr
    password: str


class NewUserPassword(BaseModel):
    password: str


class UserPreferences(BaseModel):
    birth_date: str
    biological_sex: BiologicalSex
    measurement_system: MeasurementSystem
    height: int
    current_weight: int
    weight_goal: int
    meal_prep_time: str
    activity_level: str
    avoid_foods: list[str] = []
    preferred_cuisines: list[str] = []
    health_conditions: list[str] = []


class CreateUser(BaseModel):
    connection: str = settings.AUTH0_DEFAULT_DB_CONNECTION
    email: EmailStr
    password: str
    name: str
    verify_email: bool = True
    email_verified: typing.Optional[bool] = False
    nickname: typing.Optional[str] = None
    preferences: UserPreferences
