from pydantic import BaseModel


class MealImageThumbnail(BaseModel):
    size: int
    url: str


class MealImage(BaseModel):
    images: list[MealImageThumbnail]


class MealRecipe(BaseModel):
    recipe: str


class Meal(BaseModel):
    key: str
    full_name: str
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
