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


class CreateUser(BaseModel):
    connection: str = settings.AUTH0_DEFAULT_DB_CONNECTION
    email: EmailStr
    password: str
    name: str
    verify_email: bool = True
    email_verified: typing.Optional[bool] = False
    nickname: typing.Optional[str] = None
    personal_info: PersonalInfo
