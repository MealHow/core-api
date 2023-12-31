import typing
from enum import Enum

from mealhow_sdk import enums
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


class Auth0AccountBase(BaseModel):
    name: str
    email: EmailStr
    email_verified: typing.Optional[bool] = False
    nickname: typing.Optional[str] = None


class Auth0AccountInfo(Auth0AccountBase):
    picture: str
    updated_at: str
    sub: str
    email_verified: bool


class PersonalInfo(BaseModel):
    age: int
    biological_sex: BiologicalSex
    measurement_system: MeasurementSystem
    height: int
    current_weight: int
    weight_goal: int
    goal: enums.Goal
    activity_level: enums.ActivityLevel
    meal_prep_time: enums.MealPrepTime | None = None
    protein_goal: enums.ProteinGoal | None = None
    avoid_ingredients: list[enums.IngredientsToAvoid] = []
    preferred_cuisines: list[enums.Cuisine] = []
    health_conditions: list[enums.HealthIssue] = []
    platform: enums.Platform = enums.Platform.web


class PatchPersonalInfo(BaseModel):
    age: int | None = None
    biological_sex: BiologicalSex | None = None
    measurement_system: MeasurementSystem | None = None
    height: int | None = None
    current_weight: int | None = None
    weight_goal: int | None = None
    goal: enums.Goal | None = None
    activity_level: enums.ActivityLevel | None = None
    meal_prep_time: enums.MealPrepTime | None = None
    protein_goal: enums.ProteinGoal | None = None
    avoid_ingredients: list[enums.IngredientsToAvoid] | None = None
    preferred_cuisines: list[enums.Cuisine] | None = None
    health_conditions: list[enums.HealthIssue] | None = None


class Profile(BaseModel):
    personal_info: PersonalInfo
    auth0_account: Auth0AccountInfo


class CreateUser(Auth0AccountBase):
    connection: str = settings.AUTH0_DEFAULT_DB_CONNECTION
    password: str
    verify_email: bool = True
    personal_info: PersonalInfo
