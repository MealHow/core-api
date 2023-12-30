import asyncio
import json

from fastapi import Request
from google.cloud import ndb
from mealhow_sdk import enums
from mealhow_sdk.datastore_models import MealPlan, User

from core.config import get_settings

settings = get_settings()


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


async def request_new_meal_plan(request: Request) -> str:
    topic = "projects/{project_id}/topics/{topic}".format(
        project_id=settings.PROJECT_ID,
        topic=settings.PUBSUB_MEAL_PLAN_EVENT_TOPIC_ID,
    )

    # TODO: Calculate new calories goal and user's age

    input_data = {"user_id": request.state.user_id}
    data = json.dumps(input_data).encode("utf-8")
    request.state.pubsub_publisher.publish(topic, data)

    meal_plan = None
    while not meal_plan:
        await asyncio.sleep(1)
        meal_plan = await get_in_progress_meal_plan(request.state.user_id)

    return meal_plan.key.id()
