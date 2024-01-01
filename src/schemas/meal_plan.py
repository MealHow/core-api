from datetime import datetime

from mealhow_sdk import enums
from pydantic import BaseModel


class CreateMealPlanResponse(BaseModel):
    meal_plan_id: int


class MealPlanItem(BaseModel):
    id: str  # noqa: A003, VNE003
    meal_name: str
    meal_time: str
    day: int
    preparation_time: int
    calories: int
    protein: int
    carbs: int
    fats: int


class MealPlanDayTotalInfo(BaseModel):
    calories: int
    protein: int
    carbs: int
    fats: int


class MealPlanDayItem(BaseModel):
    meals: list[MealPlanItem]
    total: MealPlanDayTotalInfo


class MealPlanDetails(BaseModel):
    day_1: MealPlanDayItem
    day_2: MealPlanDayItem
    day_3: MealPlanDayItem
    day_4: MealPlanDayItem
    day_5: MealPlanDayItem
    day_6: MealPlanDayItem
    day_7: MealPlanDayItem


class MealPlan(BaseModel):
    key: int
    status: enums.MealPlanStatus
    details: MealPlanDetails | None
    created_at: datetime
