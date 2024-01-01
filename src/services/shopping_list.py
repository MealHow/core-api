import datetime
from typing import Any

from google.cloud import ndb
from mealhow_sdk import external_api, parsers, prompt_templates
from mealhow_sdk.datastore_models import Meal, ShoppingList, ShoppingListItem, User

from core import custom_exceptions
from core.config import get_settings
from schemas.shopping_list import ShoppingListRequest

settings = get_settings()


async def get_shopping_lists_from_db(user_id: str) -> list[ShoppingList]:
    return (
        ShoppingList.query()
        .filter(
            ndb.AND(
                ShoppingList.user == ndb.Key(User, user_id),
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


async def delete_shopping_list_from_db(user_id: str, key: int) -> None:
    shopping_list = await get_shopping_list_by_key_from_db(user_id, key)
    shopping_list.deleted_at = datetime.datetime.utcnow()
    shopping_list.put()


async def create_new_shopping_list_in_db(user_id: str, data: ShoppingListRequest) -> ShoppingList:
    meal_keys = [ndb.Key(Meal, meal_id) for meal_id in data.meal_ids]
    meals = ndb.get_multi(meal_keys)
    meals_list_text = "\n".join([f"- {meal.full_name} ({meal.calories} calories)" for meal in meals])

    response = await external_api.openai_get_gpt_response(
        model=settings.OPENAI_GPT_MODEL_VERSION,
        text_request=prompt_templates.SHOPPING_LIST_REQUEST.format(meals_list=meals_list_text),
    )
    parsed_shopping_list = await parsers.parse_shopping_list(response)
    shopping_list = ShoppingList(
        user=ndb.Key(User, user_id),
        name=data.name.strip().lower(),
        linked_meals=meal_keys,
        items=[ShoppingListItem(name=item["product_name"], quantity=item["quantity"]) for item in parsed_shopping_list],
    )
    shopping_list_key = shopping_list.put()
    return shopping_list_key.get()


async def get_linked_meals_to_shopping_list_from_db(user_id: str, key: int) -> list[dict[str, Any]]:
    shopping_list = await get_shopping_list_by_key_from_db(user_id, key)
    meal_entities = ndb.get_multi(shopping_list.linked_meals)
    meals = [meal.to_dict() for meal in meal_entities]

    for meal in meals:
        meal["image"] = meal["image"].get().to_dict()

    return meals
