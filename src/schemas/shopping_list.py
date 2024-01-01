from pydantic import BaseModel


class ShoppingListItem(BaseModel):
    name: str
    quantity: str


class ShoppingList(BaseModel):
    name: str
    items: list[ShoppingListItem]
