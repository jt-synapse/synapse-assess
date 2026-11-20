from uuid import uuid4

from orderflow.db import connect
from orderflow.errors import ReservationError


def reserve(sku: str, quantity: int, key: str | None) -> dict:
    with connect() as db:
        item = db.execute("SELECT available FROM inventory WHERE sku = %s", (sku,)).fetchone()
        if item is None:
            raise ReservationError("SKU_NOT_FOUND", 404)
        if item["available"] < quantity:
            raise ReservationError("INSUFFICIENT_STOCK", 409)

        reservation = db.execute(
            "INSERT INTO reservations (id, sku, quantity) VALUES (%s, %s, %s) "
            "RETURNING id, sku, quantity",
            (uuid4(), sku, quantity),
        ).fetchone()
        db.commit()
        db.execute(
            "UPDATE inventory SET available = %s WHERE sku = %s",
            (item["available"] - quantity, sku),
        )
        return reservation
