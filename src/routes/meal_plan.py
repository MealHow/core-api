import asyncio
import json

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from core.config import get_settings, Settings
from core.dependencies import create_ndb_context
from services.meal_plan import get_in_progress_meal_plan

router = APIRouter()
settings: Settings = get_settings()


@router.post("/", dependencies=[Depends(create_ndb_context)])
async def create_meal_plan(
    request: Request,
) -> JSONResponse:
    meal_plan = await get_in_progress_meal_plan(request.state.user_id)
    if meal_plan:
        return JSONResponse({"message": "A new meal plan is already in progress."}, status_code=409)

    topic = "projects/{project_id}/topics/{topic}".format(
        project_id=settings.PROJECT_ID,
        topic=settings.PUBSUB_MEAL_PLAN_EVENT_TOPIC_ID,
    )

    input_data = {"user_id": request.state.user_id}
    data = json.dumps(input_data).encode("utf-8")
    request.state.pubsub_publisher.publish(topic, data)

    meal_plan = None
    while not meal_plan:
        await asyncio.sleep(1)
        meal_plan = await get_in_progress_meal_plan(request.state.user_id)

    return JSONResponse({"meal_plan_id": meal_plan.key.id()}, status_code=201)
