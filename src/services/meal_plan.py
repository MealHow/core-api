from google.cloud import ndb
from mealhow_sdk import enums
from mealhow_sdk.datastore_models import MealPlan, User


async def get_in_progress_meal_plan(user_id: str) -> MealPlan:
    return (
        MealPlan.query()
        .filter(
            ndb.AND(
                MealPlan.user == ndb.Key(User, user_id),
                MealPlan.status == enums.MealPlanStatus.in_progress.name,
            )
        )
        .get()
    )
