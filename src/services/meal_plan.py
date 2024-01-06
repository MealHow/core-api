import asyncio
import datetime
import json
from typing import Any

import mealhow_sdk
from dateutil.relativedelta import relativedelta
from fastapi import Request
from google.cloud import ndb
from mealhow_sdk import enums, prompt_templates
from mealhow_sdk.datastore_models import MealPlan, User

from core import custom_exceptions
from core.config import get_settings
from core.custom_exceptions import CreateMealPlanTimeoutException
from core.helpers import get_pubsub_topic
from schemas.user import PatchPersonalInfo, PersonalInfo
from services.user import calculate_weight_and_height, get_bmr_and_total_calories_goal

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
    meal_plan = (
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

    if not meal_plan:
        raise custom_exceptions.NotFoundException("Meal plan not found")

    return meal_plan


async def get_archived_meal_plans_from_db(user_id: str) -> list[MealPlan]:
    return (
        MealPlan.query()
        .filter(
            ndb.AND(
                MealPlan.user == ndb.Key(User, user_id),
                MealPlan.status == enums.MealPlanStatus.archived.name,
            )
        )
        .order(-MealPlan.created_at)
        .fetch()
    )


async def request_new_meal_plan(request: Request) -> str:
    topic = await get_pubsub_topic(settings.PUBSUB_MEAL_PLAN_EVENT_TOPIC_ID)

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


async def request_meal_plan_preview(data: PersonalInfo) -> dict[int, dict[str, Any]]:
    body_params = await calculate_weight_and_height(data)
    _, calories_goal = await get_bmr_and_total_calories_goal(body_params, data)
    prompt = await mealhow_sdk.get_openai_meal_plan_prompt(
        mealhow_sdk.MealPlanPromptInputData(
            calories_goal=calories_goal,
            protein_goal=data.protein_goal,
            preparation_time=data.meal_prep_time,
            preferred_cuisines=data.preferred_cuisines,
            ingredients_to_avoid=data.avoid_ingredients,
            health_issues=data.health_conditions,
        ),
        base_prompt=prompt_templates.MEAL_PLAN_PREVIEW_BASE_PROMPT,
    )

    parsed_diet_plans = await mealhow_sdk.request_meal_plans(
        request_body=prompt,
        gpt_model=settings.OPENAI_GPT_MODEL_VERSION,
    )
    return await mealhow_sdk.compound_most_optimal_meal_plan(
        diet_plan_variations=parsed_diet_plans,
        daily_calories_goal=calories_goal,
        plan_length=1,
    )
