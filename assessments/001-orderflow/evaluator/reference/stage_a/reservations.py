from orderflow.atomic import allocate
from orderflow.db import connect


def reserve(sku: str, quantity: int, key: str | None) -> dict:
    with connect() as db:
        return allocate(db, sku, quantity)
