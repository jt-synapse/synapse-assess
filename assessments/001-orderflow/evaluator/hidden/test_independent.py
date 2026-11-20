from .probes import balance, forbid_update, order, race


def test_competing_orders(db, client, stock, starter):
    sku = stock(1)
    responses = race(db, client, sku, (None, None))
    statuses = sorted(response.status_code for response in responses)
    if starter:
        assert statuses == [201, 201]
        assert balance(db, sku) == (0, 2)
    else:
        assert statuses == [201, 409]
        assert balance(db, sku) == (0, 1)


def test_database_failure_rolls_back(db, client, stock, starter):
    sku = stock(2)
    forbid_update(db, sku, 1)
    response = order(client, sku)
    assert response.status_code == 503
    assert balance(db, sku) == (2, 1 if starter else 0)
