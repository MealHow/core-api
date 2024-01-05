import datetime
import json
from typing import Any

from fastapi import Request
from google.cloud import ndb
from mealhow_sdk import enums
from mealhow_sdk.datastore_models import FavoriteMeal, Meal, MealImage, User

from core import custom_exceptions
from core.config import get_settings

settings = get_settings()


async def get_meal_from_db_by_key(key: str) -> Meal:
    meal = Meal.get_by_id(key)
    if not meal:
        raise custom_exceptions.NotFoundException("Meal not found")

    return meal


async def create_and_save_meal_recipe(request: Request, meal: Meal) -> Meal:
    topic = "projects/{project_id}/topics/{topic}".format(
        project_id=settings.PROJECT_ID,
        topic=settings.PUBSUB_MEAL_RECIPE_EVENT_TOPIC_ID,
    )
    event_body = json.dumps({"meal_id": meal.key.id()}).encode("utf-8")
    request.state.pubsub_publisher.publish(topic, event_body)

    meal.recipe_status = enums.JobStatus.in_progress.name
    return meal.put().get()


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


async def unmark_meals_as_favorite(user_id: str, meal_keys: list[int]) -> None:
    favorite_meals = (
        FavoriteMeal.query()
        .filter(
            ndb.AND(
                FavoriteMeal.user == ndb.Key(User, user_id),
                FavoriteMeal.meal.IN([ndb.Key(Meal, meal_key) for meal_key in meal_keys]),
                FavoriteMeal.deleted_at == None,  # noqa: E711
            )
        )
        .fetch()
    )

    for meal in favorite_meals:
        meal.deleted_at = datetime.datetime.now()

    ndb.put_multi(favorite_meals)
