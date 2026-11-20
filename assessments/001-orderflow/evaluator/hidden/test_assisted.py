from uuid import uuid4

from psycopg import sql

from .probes import balance, forbid_update, order, race


def test_replay_equivalent_request_and_reject_conflicting_payload(db, client, stock):
    key, sku = uuid4().hex, stock(2)
    original = order(client, sku, key=key)
    replay = client.post(
        "/reservations", json={"quantity": 1, "sku": sku}, headers={"Idempotency-Key": key}
    )
    assert original.status_code == replay.status_code == 201
    assert original.json() == replay.json()
    for conflict in (order(client, sku, quantity=2, key=key), order(client, stock(2), key=key)):
        assert conflict.status_code == 409
        assert conflict.json()["detail"] == "IDEMPOTENCY_CONFLICT"
    assert balance(db, sku) == (1, 1)


def test_concurrent_same_key_commits_once(db, client, stock):
    key, sku = uuid4().hex, stock(2)
    first, second = race(db, client, sku, (key, key))
    assert first.status_code == second.status_code == 201
    assert first.json() == second.json()
    assert balance(db, sku) == (1, 1)


def test_distinct_keys_preserve_stock(db, client, stock):
    sku = stock(1)
    responses = race(db, client, sku, (uuid4().hex, uuid4().hex))
    assert sorted(response.status_code for response in responses) == [201, 409]
    assert balance(db, sku) == (0, 1)


def test_validation_stock_and_transaction_failures_release_the_key(db, client, stock):
    key, sku = uuid4().hex, stock(0)
    assert order(client, sku, quantity=0, key=key).status_code == 422
    assert order(client, uuid4().hex, key=key).status_code == 404
    assert order(client, sku, key=key).status_code == 409
    db.execute("UPDATE inventory SET available=2 WHERE sku=%s", (sku,))
    constraint = forbid_update(db, sku, 1)
    assert order(client, sku, key=key).status_code == 503
    assert balance(db, sku) == (2, 0)
    db.execute(sql.SQL("ALTER TABLE inventory DROP CONSTRAINT {}").format(constraint))
    assert order(client, sku, key=key).status_code == 201
    assert balance(db, sku) == (1, 1)
