from orderflow.atomic import allocate
from orderflow.db import connect
from orderflow.errors import ReservationError


def reserve(sku: str, quantity: int, key: str | None) -> dict:
    with connect() as db:
        if key is None:
            return allocate(db, sku, quantity)

        # Serialize equal keys across workers until this transaction ends.
        # A hash collision adds waiting only. The lookup uses the full key.
        db.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (key,))
        previous = db.execute(
            "SELECT r.id, r.sku, r.quantity FROM reservation_keys k "
            "JOIN reservations r ON r.id = k.reservation_id WHERE k.request_key = %s",
            (key,),
        ).fetchone()
        if previous:
            if (previous["sku"], previous["quantity"]) != (sku, quantity):
                raise ReservationError("IDEMPOTENCY_CONFLICT", 409)
            return previous

        result = allocate(db, sku, quantity)
        db.execute("INSERT INTO reservation_keys VALUES (%s, %s)", (key, result["id"]))
        return result
