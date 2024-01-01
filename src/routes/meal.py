from fastapi import APIRouter, Depends, Request, status

from core.config import get_settings, Settings
from core.dependencies import create_ndb_context
from schemas.exception import ExceptionResponse
from schemas.meal import Meal, MealResponse
from services.meal import (
    create_and_save_meal_recipe,
    create_image_artifact_report,
    get_favorite_meals_from_db,
    get_meal_from_db_by_key,
    save_meal_as_favorite_in_db,
    unmark_meal_as_favorite,
)

router = APIRouter()
settings: Settings = get_settings()


@router.get(
    "/favorite",
    status_code=status.HTTP_200_OK,
    response_model=list[Meal],
    dependencies=[Depends(create_ndb_context)],
)
async def get_favorite_meals(request: Request) -> list[Meal]:
    favorite_meals = await get_favorite_meals_from_db(request.state.user_id)
    return [Meal(**meal) for meal in favorite_meals]


@router.post(
    "/{key}/favorite",
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ExceptionResponse, "description": "Meal not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def add_meal_to_favorites(request: Request, key: str) -> None:
    await save_meal_as_favorite_in_db(request.state.user_id, key)


@router.delete(
    "/{key}/favorite",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ExceptionResponse, "description": "Meal not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def delete_favorite_meal(request: Request, key: str) -> None:
    await unmark_meal_as_favorite(request.state.user_id, key)


@router.get(
    "/{key}",
    status_code=status.HTTP_200_OK,
    response_model=MealResponse,
    responses={404: {"model": ExceptionResponse, "description": "Meal not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def get_meal_by_key(key: str) -> MealResponse:
    meal_entity = await get_meal_from_db_by_key(key)

    if not meal_entity.recipe and meal_entity.preparation_time > 2:
        meal_entity = await create_and_save_meal_recipe(meal_entity)

    meal = meal_entity.to_dict()
    meal["image"] = meal_entity.image.get().to_dict()
    if meal_entity.recipe:
        meal["recipe"] = meal_entity.recipe.get().to_dict()

    return MealResponse(**meal)


@router.post(
    "/{key}/image/report-artifact",
    status_code=status.HTTP_201_CREATED,
    responses={404: {"model": ExceptionResponse, "description": "Meal image not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def report_image_artifact(key: str) -> None:
    await create_image_artifact_report(key)
