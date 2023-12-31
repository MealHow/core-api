import datetime
from typing import Any

import pycountry
from dateutil.relativedelta import relativedelta
from fastapi import Request
from google.cloud import ndb
from mealhow_sdk import datastore_models, enums, helpers
from timezonefinder import TimezoneFinder

from core.config import get_settings
from schemas.user import CreateUser, PatchPersonalInfo, PersonalInfo

settings = get_settings()
tf = TimezoneFinder()


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


async def extract_data_from_headers(request: Request) -> dict[str, Any]:
    country_iso_code = request.headers.get(settings.CLIENT_COUNTRY_HEADER)
    subdivision_iso_code = request.headers.get(settings.CLIENT_COUNTRY_SUBDIVISION_HEADER)
    location = request.headers.get(settings.CLIENT_LAT_LONG_HEADER).split(",")
    return {
        "cdn_cache_id": request.headers.get(settings.CLIENT_CDN_CACHE_ID_HEADER),
        "client_protocol": request.headers.get(settings.CLIENT_PROTOCOL_HEADER),
        "timezone": tf.timezone_at(lat=float(location[0].strip()), lng=float(location[1].strip())),
        "country": pycountry.countries.get(alpha_2=country_iso_code).name if country_iso_code else None,
        "country_subdivision": pycountry.subdivisions.get(code=subdivision_iso_code).name
        if subdivision_iso_code
        else None,
    }


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


async def create_user_db_entity(request: Request, user_obj: CreateUser, user_id: str, stripe_customer_id: str) -> None:
    body_params = await calculate_weight_and_height(user_obj.personal_info)
    bmr, calories_goal = await get_bmr_and_total_calories_goal(body_params, user_obj.personal_info)

    key = ndb.Key(datastore_models.User, user_id)
    user_entity = datastore_models.User(
        key=key,
        email=user_obj.email,
        goal=user_obj.personal_info.goal,
        birth_year=datetime.datetime.now() - relativedelta(years=int(user_obj.personal_info.age)),
        biological_sex=user_obj.personal_info.biological_sex,
        meal_prep_time=user_obj.personal_info.meal_prep_time,
        activity_level=user_obj.personal_info.activity_level,
        measurement_system=user_obj.personal_info.measurement_system,
        protein_goal=user_obj.personal_info.protein_goal,
        avoid_foods=user_obj.personal_info.avoid_ingredients,
        preferred_cuisines=user_obj.personal_info.preferred_cuisines,
        health_conditions=user_obj.personal_info.health_conditions,
        height_cm=body_params["height_cm"],
        height_inches=body_params["height_inches"],
        current_weight=[await get_weight_record(body_params, "current_weight")],
        weight_goal=[await get_weight_record(body_params, "weight_goal")],
        bmr=bmr,
        calories_goal=calories_goal,
        stripe_customer_id=stripe_customer_id,
        platform=user_obj.personal_info.platform,
        **(await extract_data_from_headers(request)),
    )
    user_entity.put()
