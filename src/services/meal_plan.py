import asyncio
import datetime
import json

from dateutil.relativedelta import relativedelta
from fastapi import Request
from google.cloud import ndb
from mealhow_sdk import enums
from mealhow_sdk.datastore_models import MealPlan, User

from core.config import get_settings
from core.custom_exceptions import CreateMealPlanTimeoutException
from schemas.user import PatchPersonalInfo
from services.user import get_bmr_and_total_calories_goal

settings = get_settings()


async def get_in_progress_meal_plan_from_db(user_id: str) -> MealPlan:
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


async def get_current_meal_plan_from_db(user_id: str) -> MealPlan:
    return (
        MealPlan.query()
        .filter(
            ndb.AND(
                MealPlan.user == ndb.Key(User, user_id),
                ndb.OR(
                    MealPlan.status == enums.MealPlanStatus.in_progress.name,
                    MealPlan.status == enums.MealPlanStatus.failed.name,
                    MealPlan.status == enums.MealPlanStatus.active.name,
                ),
            )
        )
        .get()
    )


async def request_new_meal_plan(request: Request) -> str:
    topic = "projects/{project_id}/topics/{topic}".format(
        project_id=settings.PROJECT_ID,
        topic=settings.PUBSUB_MEAL_PLAN_EVENT_TOPIC_ID,
    )

    user_id = request.state.user_id
    user = User.get_by_id(user_id)

    current_weight = sorted(user.current_weight, key=lambda x: x.created_at, reverse=True)[0]
    bmr, calories_goal = await get_bmr_and_total_calories_goal(
        {
            "current_weight_kg": current_weight.weight_kg,
            "height_cm": user.height_cm,
        },
        PatchPersonalInfo(
            activity_level=user.activity_level,
            goal=user.goal,
            biological_sex=user.biological_sex,
            age=relativedelta(datetime.datetime.now(), user.birth_year).years,
        ),
    )
    user.bmr = bmr
    user.calories_goal = calories_goal
    user.put()

    data = json.dumps({"user_id": user_id}).encode("utf-8")
    request.state.pubsub_publisher.publish(topic, data)

    meal_plan = None
    number_of_retries = 0
    while not meal_plan:
        await asyncio.sleep(1)
        meal_plan = await get_in_progress_meal_plan_from_db(user_id)
        number_of_retries += 1
        if number_of_retries == 30:
            raise CreateMealPlanTimeoutException

    return meal_plan.key.id()
