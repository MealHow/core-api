from fastapi import Request
from google.cloud import ndb
from mealhow_sdk.datastore_models import User


async def create_new_user(user_id: int, data: dict, request: Request) -> None:
    key_a = ndb.Key(User, user_id)
    person = User(
        key=key_a,
    )
    person.put()
