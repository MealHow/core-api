import datetime
import json
from typing import Any

from fastapi import Request
from google.cloud import ndb
from mealhow_sdk import enums
from mealhow_sdk.datastore_models import Meal, ShoppingList, ShoppingListItem, User

from core import custom_exceptions
from core.config import get_settings
from core.helpers import get_pubsub_topic
from schemas.shopping_list import ShoppingListRequest, UpdateShoppingListRequest

settings = get_settings()


async def get_users_shopping_lists_from_db(user_id: str) -> list[ShoppingList]:
    return (
        ShoppingList.query()
        .order(ShoppingList.status)
        .filter(
            ndb.AND(
                ShoppingList.user == ndb.Key(User, user_id),
                ShoppingList.status != enums.JobStatus.failed.name,
                ShoppingList.deleted_at == None,  # noqa: E711
            )
        )
        .order(-ShoppingList.created_at)
        .fetch()
    )


async def get_shopping_list_by_key_from_db(user_id: str, key: int) -> ShoppingList:
    shopping_list = (
        ShoppingList.query()
        .filter(
            ndb.AND(
                ShoppingList.user == ndb.Key(User, user_id),
                ShoppingList.key == ndb.Key(ShoppingList, key),
                ShoppingList.deleted_at == None,  # noqa: E711
            )
        )
        .get()
    )

    if not shopping_list:
        raise custom_exceptions.NotFoundException("Shopping list not found")

    return shopping_list


async def get_shopping_lists_from_db(user_id: str, keys: list[int]) -> list[ShoppingList]:
    filtered_shopping_lists = []
    if len(keys) == 1:
        filtered_shopping_lists = [await get_shopping_list_by_key_from_db(user_id, keys[0])]
    elif not keys:
        return []
    else:
        shopping_lists = ndb.get_multi([ndb.Key(ShoppingList, key) for key in keys])

        for shopping_list in shopping_lists:
            if shopping_list.user.id() == user_id and not shopping_list.deleted_at:
                filtered_shopping_lists.append(shopping_list)

    return filtered_shopping_lists


async def delete_shopping_lists_from_db(user_id: str, keys: list[int]) -> None:
    shopping_lists = await get_shopping_lists_from_db(user_id, keys)
    for shopping_list in shopping_lists:
        shopping_list.deleted_at = datetime.datetime.utcnow()

    ndb.put_multi(shopping_lists)


async def create_new_shopping_list_in_db(request: Request, data: ShoppingListRequest) -> ShoppingList:
    meal_keys = [ndb.Key(Meal, meal_id) for meal_id in data.meal_ids]
    shopping_list = ShoppingList(
        user=ndb.Key(User, request.state.user_id),
        name=data.name.strip().lower(),
        linked_meals=meal_keys,
        status=enums.JobStatus.in_progress.name,
    )
    shopping_list_key = shopping_list.put()
    shopping_list_entity = shopping_list_key.get()

    topic = await get_pubsub_topic(settings.PUBSUB_SHOPPING_LIST_EVENT_TOPIC_ID)
    event_body = json.dumps(
        {
            "shopping_list_id": shopping_list_entity.key.id(),
            "meal_ids": data.meal_ids,
        }
    ).encode("utf-8")
    request.state.pubsub_publisher.publish(topic, event_body)

    return shopping_list_entity


async def get_linked_meals_to_shopping_list_from_db(user_id: str, key: int) -> list[dict[str, Any]]:
    shopping_list = await get_shopping_list_by_key_from_db(user_id, key)
    meal_entities = ndb.get_multi(shopping_list.linked_meals)
    meals = [meal.to_dict() for meal in meal_entities]

    for meal in meals:
        meal["image"] = meal["image"].get().to_dict()

    return meals


async def update_shopping_list_by_key_in_db(user_id: str, key: int, data: UpdateShoppingListRequest) -> ShoppingList:
    shopping_list = await get_shopping_list_by_key_from_db(user_id, key)
    shopping_list.name = data.name.strip().lower()
    shopping_list.items = [ShoppingListItem(**i.model_dump()) for i in data.items]
    shopping_list.put()

    return shopping_list
