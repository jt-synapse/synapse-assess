from concurrent.futures import ThreadPoolExecutor
from time import monotonic, sleep
from uuid import uuid4

from psycopg import sql


def order(client, sku, quantity=1, key=None):
    headers = {} if key is None else {"Idempotency-Key": key}
    return client.post("/reservations", json={"sku": sku, "quantity": quantity}, headers=headers)


def balance(db, sku):
    return db.execute(
        "SELECT available, (SELECT count(*) FROM reservations WHERE sku = i.sku) "
        "FROM inventory i WHERE sku = %s",
        (sku,),
    ).fetchone()


def race(db, client, sku, keys):
    # Hold the stock row until PostgreSQL observes two distinct blocked requests.
    # This gives both starter requests time to read the old value and also
    # supports solutions that block on a row lock or an idempotency key.
    with ThreadPoolExecutor(max_workers=2) as pool:
        with db.transaction():
            db.execute("SELECT sku FROM inventory WHERE sku=%s FOR NO KEY UPDATE", (sku,))
            futures = [pool.submit(order, client, sku, 1, key) for key in keys]
            deadline = monotonic() + 6
            while monotonic() < deadline:
                db.execute("SELECT pg_stat_clear_snapshot()")
                count = db.execute(
                    "SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                    "AND pid <> pg_backend_pid() AND cardinality(pg_blocking_pids(pid)) > 0"
                ).fetchone()[0]
                if count >= 2:
                    break
                sleep(0.02)
            else:
                raise AssertionError("Did not observe two blocked PostgreSQL sessions")
        return [future.result(timeout=10) for future in futures]


def forbid_update(db, sku, forbidden_balance):
    constraint = sql.Identifier("forced_failure_" + uuid4().hex)
    db.execute(
        sql.SQL(
            "ALTER TABLE inventory ADD CONSTRAINT {} CHECK (sku <> {} OR available <> {})"
        ).format(constraint, sql.Literal(sku), sql.Literal(forbidden_balance))
    )
    return constraint
