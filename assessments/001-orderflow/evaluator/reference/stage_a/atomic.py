from uuid import uuid4

from orderflow.errors import ReservationError


def allocate(db, sku: str, quantity: int) -> dict:
    updated = db.execute(
        "UPDATE inventory SET available = available - %s "
        "WHERE sku = %s AND available >= %s RETURNING sku",
        (quantity, sku, quantity),
    ).fetchone()
    if updated is None:
        exists = db.execute("SELECT 1 FROM inventory WHERE sku = %s", (sku,)).fetchone()
        if exists is None:
            raise ReservationError("SKU_NOT_FOUND", 404)
        raise ReservationError("INSUFFICIENT_STOCK", 409)
    return db.execute(
        "INSERT INTO reservations (id, sku, quantity) VALUES (%s, %s, %s) "
        "RETURNING id, sku, quantity",
        (uuid4(), sku, quantity),
    ).fetchone()
