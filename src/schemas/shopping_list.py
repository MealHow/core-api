from mealhow_sdk import enums
from pydantic import BaseModel


class ShoppingListItem(BaseModel):
    name: str
    quantity: str


class ShoppingList(BaseModel):
    key: int
    name: str
    status: enums.JobStatus


class ShoppingListWithCount(ShoppingList):
    total_items: int


class ShoppingListWithItems(ShoppingList):
    items: list[ShoppingListItem]


class ShoppingListRequest(BaseModel):
    name: str
    meal_ids: list[str]
