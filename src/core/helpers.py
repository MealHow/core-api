from fastapi.routing import APIRoute


def custom_generate_unique_id(route: APIRoute) -> str:
    try:
        return f"{route.tags[0]}-{route.name}"
    except IndexError:
        return route.name
