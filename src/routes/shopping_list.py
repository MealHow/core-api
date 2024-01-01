from fastapi import APIRouter, Depends, Request, status

from core.config import get_settings, Settings
from core.dependencies import create_ndb_context
from schemas.exception import ExceptionResponse
from schemas.meal import Meal
from schemas.shopping_list import (
    ShoppingListRequest,
    ShoppingListWithCount,
    ShoppingListWithItems,
)
from services.shopping_list import (
    create_new_shopping_list_in_db,
    delete_shopping_list_from_db,
    get_linked_meals_to_shopping_list_from_db,
    get_shopping_list_by_key_from_db,
    get_shopping_lists_from_db,
)

router = APIRouter()
settings: Settings = get_settings()


@router.get(
    "/",
    status_code=status.HTTP_200_OK,
    response_model=list[ShoppingListWithCount],
    dependencies=[Depends(create_ndb_context)],
)
async def get_shopping_lists(request: Request) -> list[ShoppingListWithCount]:
    shopping_lists = await get_shopping_lists_from_db(request.state.user_id)
    shopping_lists_with_count = []
    for shopping_list in shopping_lists:
        shopping_lists_with_count.append(
            ShoppingListWithCount(**shopping_list.to_dict(), total_items=len(shopping_list.items))
        )

    return shopping_lists_with_count


@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=ShoppingListWithItems,
    dependencies=[Depends(create_ndb_context)],
)
async def create_shopping_list(request: Request, data: ShoppingListRequest) -> ShoppingListWithItems:
    shopping_list = await create_new_shopping_list_in_db(request.state.user_id, data)
    return ShoppingListWithItems(**shopping_list.to_dict())


@router.get(
    "/{key}",
    status_code=status.HTTP_200_OK,
    response_model=ShoppingListWithItems,
    responses={404: {"model": ExceptionResponse, "description": "Shopping list not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def get_shopping_list_by_key(request: Request, key: int) -> ShoppingListWithItems:
    shopping_list = await get_shopping_list_by_key_from_db(request.state.user_id, key)
    return ShoppingListWithItems(**shopping_list.to_dict())


@router.get(
    "/{key}/meals",
    status_code=status.HTTP_200_OK,
    response_model=list[Meal],
    responses={404: {"model": ExceptionResponse, "description": "Shopping list not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def get_linked_meals_to_shopping_list(request: Request, key: int) -> list[Meal]:
    linked_meals = await get_linked_meals_to_shopping_list_from_db(request.state.user_id, key)
    return [Meal(**meal) for meal in linked_meals]


@router.delete(
    "/{key}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"model": ExceptionResponse, "description": "Shopping list not found"}},
    dependencies=[Depends(create_ndb_context)],
)
async def delete_shopping_list(request: Request, key: int) -> None:
    await delete_shopping_list_from_db(request.state.user_id, key)
