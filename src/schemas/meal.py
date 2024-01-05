from mealhow_sdk import enums
from pydantic import BaseModel


class MealImageThumbnail(BaseModel):
    size: int
    url: str


class MealImage(BaseModel):
    images: list[MealImageThumbnail]


class MealRecipe(BaseModel):
    text: str
    ingredients: list[str] | None


class Meal(BaseModel):
    key: str
    full_name: str
    recipe_status: enums.JobStatus | None
    calories: int
    protein: int
    carbs: int
    fats: int
    image: MealImage
    preparation_time: int


class MealResponse(Meal):
    recipe: MealRecipe | None = None


class AddMealToFavoritesRequest(BaseModel):
    meal_id: str
