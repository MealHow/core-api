import datetime
from typing import Any

from dateutil.relativedelta import relativedelta
from mealhow_sdk import enums
from mealhow_sdk.datastore_models import User

from schemas.user import PatchPersonalInfo
from services.auth import (
    calculate_weight_and_height,
    get_bmr_and_total_calories_goal,
    get_weight_record,
)


async def get_user_personal_info_model_to_dict(user: User) -> dict[str, Any]:
    current_weight = sorted(user.current_weight, key=lambda x: x.created_at, reverse=True)[0]
    weight_goal = sorted(user.weight_goal, key=lambda x: x.created_at, reverse=True)[0]

    return {
        "age": relativedelta(datetime.datetime.now(), user.birth_year).years,
        "goal": user.goal,
        "biological_sex": user.biological_sex,
        "measurement_system": user.measurement_system,
        "activity_level": user.activity_level,
        "height": user.height_cm
        if user.measurement_system == enums.MeasurementSystem.metric.value
        else user.height_inches,
        "current_weight": current_weight.weight_kg
        if user.measurement_system == enums.MeasurementSystem.metric.value
        else current_weight.weight_lbs,
        "weight_goal": weight_goal.weight_kg
        if user.measurement_system == enums.MeasurementSystem.metric.value
        else weight_goal.weight_lbs,
        "meal_prep_time": user.meal_prep_time,
        "protein_goal": user.protein_goal,
        "avoid_ingredients": user.avoid_foods,
        "preferred_cuisines": user.preferred_cuisines,
        "health_conditions": user.health_conditions,
        "platform": user.platform,
    }


async def get_user_personal_info_from_db(user_id: str) -> dict[str, Any] | None:
    user = User.get_by_id(user_id)
    if not user:
        return None

    return await get_user_personal_info_model_to_dict(user)


async def update_user_personal_info(user_id: str, data: dict[str, Any]) -> dict[str, Any] | None:
    user = User.get_by_id(user_id)
    if not user:
        return None

    if "age" in data:
        data["birth_year"] = datetime.datetime.now() - relativedelta(years=int(data["age"]))
        del data["age"]

    measurement_system = data["measurement_system"].value if "measurement_system" in data else user.measurement_system
    current_weight = sorted(user.current_weight, key=lambda x: x.created_at, reverse=True)[0]
    weight_goal = sorted(user.weight_goal, key=lambda x: x.created_at, reverse=True)[0]
    current_weight = (
        current_weight.weight_kg
        if measurement_system == enums.MeasurementSystem.metric.value
        else current_weight.weight_lbs
    )
    weight_goal = (
        weight_goal.weight_kg if measurement_system == enums.MeasurementSystem.metric.value else weight_goal.weight_lbs
    )

    body_params = await calculate_weight_and_height(
        PatchPersonalInfo(
            measurement_system=measurement_system,
            height=data.get("height")
            or (user.height_cm if user.measurement_system == measurement_system else user.height_inches),
            current_weight=data.get("current_weight") or current_weight,
            weight_goal=data.get("weight_goal") or weight_goal,
        )
    )

    if "height" in data:
        data["height_cm"] = body_params["height_cm"]
        data["height_inches"] = body_params["height_inches"]
        del data["height"]

    if "current_weight" in data:
        user.current_weight = user.current_weight + [await get_weight_record(body_params, "current_weight")]
        del data["current_weight"]

    if "weight_goal" in data:
        user.weight_goal = user.weight_goal + [await get_weight_record(body_params, "weight_goal")]
        del data["weight_goal"]

    bmr, calories_goal = await get_bmr_and_total_calories_goal(
        body_params,
        PatchPersonalInfo(
            activity_level=data.get("activity_level") or user.activity_level,
            goal=data.get("goal") or user.goal,
            biological_sex=data.get("biological_sex") or user.biological_sex,
            age=relativedelta(datetime.datetime.now(), data.get("birth_year") or user.birth_year).years,
        ),
    )
    user.bmr = bmr
    user.calories_goal = calories_goal

    for key, value in data.items():
        setattr(user, key, value)

    user_key = user.put()
    return await get_user_personal_info_model_to_dict(user_key.get())
