from fastapi import APIRouter, Depends, Request, status

from core import custom_exceptions
from core.config import get_settings, Settings
from core.dependencies import create_ndb_context
from schemas.exception import ExceptionResponse
from schemas.meal_plan import CreateMealPlanResponse, MealPlan
from services.meal_plan import (
    get_archived_meal_plans_from_db,
    get_current_meal_plan_from_db,
    get_in_progress_meal_plan_from_db,
    request_new_meal_plan,
)

router = APIRouter()
settings: Settings = get_settings()


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=CreateMealPlanResponse,
    responses={409: {"model": ExceptionResponse, "description": "A new meal plan is already in progress"}},
    dependencies=[Depends(create_ndb_context)],
)
async def create_meal_plan(
    request: Request,
) -> CreateMealPlanResponse:
    meal_plan = await get_in_progress_meal_plan_from_db(request.state.user_id)
    if meal_plan:
        raise custom_exceptions.ConflictException("A new meal plan is already in progress")

    new_meal_plan_id = await request_new_meal_plan(request)
    print(type(new_meal_plan_id))
    return CreateMealPlanResponse(meal_plan_id=new_meal_plan_id)


@router.get(
    "/current",
    status_code=status.HTTP_200_OK,
    response_model=MealPlan,
    responses={404: {"model": ExceptionResponse, "description": "Meal plan not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def get_current_meal_plan(request: Request) -> MealPlan:
    meal_plan = await get_current_meal_plan_from_db(request.state.user_id)
    if not meal_plan:
        raise custom_exceptions.NotFoundException("Meal plan not found")

    return MealPlan(**meal_plan.to_dict())


@router.get(
    "/archived",
    status_code=status.HTTP_200_OK,
    response_model=list[MealPlan],
    dependencies=[Depends(create_ndb_context)],
)
async def get_archived_meal_plans(request: Request) -> list[MealPlan]:
    meal_plans = await get_archived_meal_plans_from_db(request.state.user_id)
    return [MealPlan(**meal_plan.to_dict()) for meal_plan in meal_plans]
