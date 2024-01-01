from typing import Any

from async_stripe import stripe


async def create_new_customer(email: str, name: str) -> Any:
    return await stripe.Customer.create(email=email, name=name)
