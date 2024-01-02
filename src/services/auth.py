import datetime
from typing import Any

import pycountry
from auth0 import Auth0Error
from auth0.authentication import GetToken
from auth0.management import Auth0
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, Request
from google.cloud import ndb
from mealhow_sdk import datastore_models
from timezonefinder import TimezoneFinder

from core.config import get_settings
from schemas.user import CreateUser, LoginUser
from services.payments import create_new_customer
from services.user import (
    calculate_weight_and_height,
    get_bmr_and_total_calories_goal,
    get_weight_record,
)

settings = get_settings()
tf = TimezoneFinder()


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


async def create_user_in_db_and_auth0(
    request: Request, auth0_mgmt_client: Auth0, auth0_token: GetToken, create_user: CreateUser
) -> dict[str, Any]:
    try:
        # Create user in auth0 db
        create_user.nickname = create_user.email
        new_user_body = dict(create_user.model_dump())
        del new_user_body["personal_info"]

        new_user_auth0_obj = await auth0_mgmt_client.users.create_async(body=new_user_body)
        customer = await create_new_customer(create_user.email, create_user.name)
        await create_user_db_entity(request, create_user, new_user_auth0_obj["user_id"], customer["id"])

        # Get access token for new user
        return await auth0_token.login_async(
            username=create_user.email,
            password=create_user.password,
            audience=settings.AUTH0_API_DEFAULT_AUDIENCE,
            scope="openid profile email",
            grant_type="password",
            realm=settings.AUTH0_DEFAULT_DB_CONNECTION,
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


async def get_access_token(auth0_token: GetToken, data: LoginUser) -> dict[str, Any]:
    try:
        return await auth0_token.login_async(
            username=data.email,
            password=data.password,
            audience=settings.AUTH0_API_DEFAULT_AUDIENCE,
            scope="openid profile email",
            realm=None,
            grant_type="password",
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)


async def get_callback_response(auth0_token: GetToken, code: str) -> dict[str, Any]:
    try:
        return await auth0_token.authorization_code_async(
            grant_type="authorization_code",
            code=code,
            redirect_uri=settings.AUTH0_CALLBACK_URL,
        )
    except Auth0Error as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
