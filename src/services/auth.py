import datetime

import pycountry
from dateutil.relativedelta import relativedelta
from fastapi import Request
from google.cloud import ndb
from mealhow_sdk import datastore_models, enums, helpers
from timezonefinder import TimezoneFinder

from core.config import get_settings
from schemas.user import CreateUser

settings = get_settings()
tf = TimezoneFinder()


async def create_user_db_entity(request: Request, user_obj: CreateUser, user_id: str, stripe_customer_id: str) -> None:
    country_iso_code = request.headers.get(settings.CLIENT_COUNTRY_HEADER)
    subdivision_iso_code = request.headers.get(settings.CLIENT_COUNTRY_SUBDIVISION_HEADER)
    cdn_cache_id = request.headers.get(settings.CLIENT_CDN_CACHE_ID_HEADER)
    client_protocol = request.headers.get(settings.CLIENT_PROTOCOL_HEADER)
    location = request.headers.get(settings.CLIENT_LAT_LONG_HEADER).split(",")
    timezone = tf.timezone_at(lat=float(location[0].strip()), lng=float(location[1].strip()))

    if user_obj.personal_info.measurement_system == enums.MeasurementSystem.metric.value:
        height_cm = user_obj.personal_info.height
        current_weight_kg = user_obj.personal_info.current_weight
        weight_goal_kg = user_obj.personal_info.weight_goal
        height_inches = await helpers.convert_height_to_imperial(height_cm)
        current_weight_lbs = await helpers.convert_weight_to_imperial(current_weight_kg)
        weight_goal_lbs = await helpers.convert_weight_to_imperial(weight_goal_kg)
    else:
        height_inches = user_obj.personal_info.height
        current_weight_lbs = user_obj.personal_info.current_weight
        weight_goal_lbs = user_obj.personal_info.weight_goal
        height_cm = await helpers.convert_height_to_metric(height_inches)
        current_weight_kg = await helpers.convert_weight_to_metric(current_weight_lbs)
        weight_goal_kg = await helpers.convert_weight_to_metric(weight_goal_lbs)

    bmr_hb = await helpers.get_basal_metabolic_rate_harris_benedict(
        weight=current_weight_kg,
        height=height_cm,
        age=user_obj.personal_info.age,
        sex=user_obj.personal_info.biological_sex,
    )
    bmr_msj = await helpers.get_basal_metabolic_rate_mifflin_st_jeor(
        weight=current_weight_kg,
        height=height_cm,
        age=user_obj.personal_info.age,
        sex=user_obj.personal_info.biological_sex,
    )
    bmr = int(round((bmr_hb + bmr_msj) / 2))
    activity_adjusted_bmr = await helpers.get_calories_goal_by_activity_level(
        bmr, user_obj.personal_info.activity_level
    )
    calories_goal = await helpers.get_calories_goal_by_goal_type(activity_adjusted_bmr, user_obj.personal_info.goal)
    calories_goal = await helpers.round_calories_goal_to_nearest_100(calories_goal)

    key = ndb.Key(datastore_models.User, user_id)
    user_entity = datastore_models.User(
        key=key,
        email=user_obj.email,
        goal=user_obj.personal_info.goal,
        age=datetime.datetime.now() - relativedelta(years=int(user_obj.personal_info.age)),
        biological_sex=user_obj.personal_info.biological_sex,
        meal_prep_time=user_obj.personal_info.meal_prep_time,
        activity_level=user_obj.personal_info.activity_level,
        measurement_system=user_obj.personal_info.measurement_system,
        protein_goal=user_obj.personal_info.protein_goal,
        avoid_foods=user_obj.personal_info.avoid_ingredients,
        preferred_cuisines=user_obj.personal_info.preferred_cuisines,
        health_conditions=user_obj.personal_info.health_conditions,
        height_cm=height_cm,
        height_inches=height_inches,
        current_weight=[
            datastore_models.WeightRecord(
                weight_lbs=current_weight_lbs,
                weight_kg=current_weight_kg,
                bmi=await helpers.get_bmi(current_weight_kg, height_cm),
            )
        ],
        weight_goal=[
            datastore_models.WeightRecord(
                weight_lbs=weight_goal_lbs,
                weight_kg=weight_goal_kg,
                bmi=await helpers.get_bmi(weight_goal_kg, height_cm),
            )
        ],
        bmr=bmr,
        calories_goal=calories_goal,
        stripe_customer_id=stripe_customer_id,
        timezone=timezone,
        platform=user_obj.personal_info.platform,
        cdn_cache_id=cdn_cache_id,
        client_protocol=client_protocol,
        country=pycountry.countries.get(alpha_2=country_iso_code).name if country_iso_code else None,
        country_subdivision=pycountry.subdivisions.get(code=subdivision_iso_code).name
        if subdivision_iso_code
        else None,
    )
    user_entity.put()
