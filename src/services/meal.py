import datetime
from typing import Any

from google.cloud import ndb
from mealhow_sdk import external_api, prompt_templates
from mealhow_sdk.datastore_models import FavoriteMeal, Meal, MealImage, MealRecipe, User

from core import custom_exceptions
from core.config import get_settings

settings = get_settings()


async def get_meal_from_db_by_key(key: str) -> Meal:
    meal = Meal.get_by_id(key)
    if not meal:
        raise custom_exceptions.NotFoundException("Meal not found")

    return meal


async def create_and_save_meal_recipe(meal: Meal) -> Meal:
    response = await external_api.openai_get_gpt_response(
        model=settings.OPENAI_GPT_MODEL_VERSION,
        text_request=prompt_templates.MEAL_RECIPE_REQUEST.format(
            meal=f"{meal.full_name} ({meal.calories} calories)",
        ),
    )

    recipe = MealRecipe(recipe=response)
    recipe_key = recipe.put()

    meal.recipe = recipe_key
    meal_key = meal.put()
    return meal_key.get()


async def create_image_artifact_report(key: str) -> None:
    meal_image = MealImage.get_by_id(key.split("-")[0])
    if not meal_image:
        raise custom_exceptions.NotFoundException("Meal image not found")

    meal_image.artifact_reported = True
    meal_image.put()


async def get_favorite_meals_from_db(user_id: str) -> list[dict[str, Any]]:
    favorite_meals = (
        FavoriteMeal.query()
        .filter(
            ndb.AND(
                FavoriteMeal.user == ndb.Key(User, user_id),
                FavoriteMeal.deleted_at == None,  # noqa: E711
            )
        )
        .order(-FavoriteMeal.created_at)
        .fetch()
    )
    meal_entities = ndb.get_multi([favorite_meal.meal for favorite_meal in favorite_meals])
    meals = [meal.to_dict() for meal in meal_entities]

    for meal in meals:
        meal["image"] = meal["image"].get().to_dict()

    return meals


async def save_meal_as_favorite_in_db(user_id: str, meal_key: str) -> None:
    meal = Meal.get_by_id(meal_key)
    if not meal:
        raise custom_exceptions.NotFoundException("Meal not found")

    favorite_meal = (
        FavoriteMeal.query()
        .filter(
            ndb.AND(
                FavoriteMeal.user == ndb.Key(User, user_id),
                FavoriteMeal.meal == ndb.Key(Meal, meal_key),
                FavoriteMeal.deleted_at != None,  # noqa: E711
            )
        )
        .get()
    )

    if favorite_meal:
        favorite_meal.deleted_at = None
    else:
        favorite_meal = FavoriteMeal(user=ndb.Key(User, user_id), meal=meal.key)

    favorite_meal.put()


async def unmark_meal_as_favorite(user_id: str, meal_key: str) -> None:
    favorite_meal = (
        FavoriteMeal.query()
        .filter(
            ndb.AND(
                FavoriteMeal.user == ndb.Key(User, user_id),
                FavoriteMeal.meal == ndb.Key(Meal, meal_key),
                FavoriteMeal.deleted_at == None,  # noqa: E711
            )
        )
        .get()
    )
    if not favorite_meal:
        raise custom_exceptions.NotFoundException("Meal not found")

    favorite_meal.deleted_at = datetime.datetime.now()
    favorite_meal.put()
