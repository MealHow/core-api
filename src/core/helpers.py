from fastapi.routing import APIRoute

from core.config import get_settings

settings = get_settings()


def custom_generate_unique_id(route: APIRoute) -> str:
    try:
        return f"{route.tags[0]}-{route.name}"
    except IndexError:
        return route.name


async def get_pubsub_topic(topic_id: str, project_id: str = settings.PROJECT_ID) -> str:
    return "projects/{project_id}/topics/{topic}".format(
        project_id=project_id,
        topic=topic_id,
    )
