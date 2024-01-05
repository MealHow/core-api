import datetime
from typing import Any

from auth0 import Auth0Error
from auth0.authentication import Database
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, Request
from mealhow_sdk import datastore_models, enums, helpers
from mealhow_sdk.datastore_models import User

from core.config import get_settings
from schemas.user import PatchPersonalInfo, PersonalInfo

settings = get_settings()


async def get_bmr_and_total_calories_goal(
    body_params: dict[str, Any], personal_info: PersonalInfo | PatchPersonalInfo
) -> tuple[int, int]:
    bmr_hb = await helpers.get_basal_metabolic_rate_harris_benedict(
        weight=body_params["current_weight_kg"],
        height=body_params["height_cm"],
        age=personal_info.age,
        sex=personal_info.biological_sex,
    )
    bmr_msj = await helpers.get_basal_metabolic_rate_mifflin_st_jeor(
        weight=body_params["current_weight_kg"],
        height=body_params["height_cm"],
        age=personal_info.age,
        sex=personal_info.biological_sex,
    )
    bmr = int(round((bmr_hb + bmr_msj) / 2))
    activity_adjusted_bmr = await helpers.get_calories_goal_by_activity_level(bmr, personal_info.activity_level)
    calories_goal = await helpers.get_calories_goal_by_goal_type(activity_adjusted_bmr, personal_info.goal)
    calories_goal = await helpers.round_calories_goal_to_nearest_100(calories_goal)

    return bmr, calories_goal


async def get_weight_record(body_params: dict[str, Any], key_prefix: str) -> datastore_models.WeightRecord:
    return datastore_models.WeightRecord(
        weight_lbs=body_params[f"{key_prefix}_lbs"],
        weight_kg=body_params[f"{key_prefix}_kg"],
        bmi=await helpers.get_bmi(body_params[f"{key_prefix}_kg"], body_params["height_cm"]),
    )


async def calculate_weight_and_height(personal_info: PersonalInfo | PatchPersonalInfo) -> dict[str, Any]:
    params = {}
    if personal_info.measurement_system == enums.MeasurementSystem.metric.value:
        params["height_cm"] = personal_info.height
        params["current_weight_kg"] = personal_info.current_weight
        params["weight_goal_kg"] = personal_info.weight_goal
        params["height_inches"] = await helpers.convert_height_to_imperial(params["height_cm"])
        params["current_weight_lbs"] = await helpers.convert_weight_to_imperial(params["current_weight_kg"])
        params["weight_goal_lbs"] = await helpers.convert_weight_to_imperial(params["weight_goal_kg"])
    else:
        params["height_inches"] = personal_info.height
        params["current_weight_lbs"] = personal_info.current_weight
        params["weight_goal_lbs"] = personal_info.weight_goal
        params["height_cm"] = await helpers.convert_height_to_metric(params["height_inches"])
        params["current_weight_kg"] = await helpers.convert_weight_to_metric(params["current_weight_lbs"])
        params["weight_goal_kg"] = await helpers.convert_weight_to_metric(params["weight_goal_lbs"])

    return params


async def get_user_personal_info_model_to_dict(user: User) -> dict[str, Any]:
    current_weight = sorted(user.current_weight, key=lambda x: x.created_at, reverse=True)[0]
    weight_goal = sorted(user.weight_goal, key=lambda x: x.created_at, reverse=True)[0]

    return {
        "email": user.email,
        "name": user.name,
        "personal_info": {
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
        },
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
    user.updated_at = datetime.datetime.now()

    for key, value in data.items():
        setattr(user, key, value)

    user_key = user.put()
    return await get_user_personal_info_model_to_dict(user_key.get())


async def create_reset_password_request(request: Request, db_client: Database) -> None:
    try:
        user = User.get_by_id(request.state.user_id)
        db_client.change_password(
            email=user.email,
            connection=settings.AUTH0_DEFAULT_DB_CONNECTION,
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
