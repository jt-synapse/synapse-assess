from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from orderflow.db import connect
from orderflow.main import app


def test_reserve_available_stock():
    sku = uuid4().hex
    with connect() as db:
        db.execute("INSERT INTO inventory VALUES (%s, 3)", (sku,))
    with TestClient(app) as client:
        response = client.post("/reservations", json={"sku": sku, "quantity": 2})
        assert response.status_code == 201
        result = response.json()
        assert UUID(result["id"])
        assert result == {"id": result["id"], "sku": sku, "quantity": 2}
        assert client.post("/reservations", json={"sku": sku, "quantity": 2}).json() == {
            "detail": "INSUFFICIENT_STOCK"
        }
    with connect() as db:
        assert (
            db.execute("SELECT available FROM inventory WHERE sku=%s", (sku,)).fetchone()[
                "available"
            ]
            == 1
        )


def test_missing_sku():
    with TestClient(app) as client:
        sku = uuid4().hex
        assert client.post("/reservations", json={"sku": sku, "quantity": 1}).status_code == 404


def test_invalid_quantities_and_extra_fields():
    with TestClient(app) as client:
        for quantity in (0, -1, "1", True, 2**31):
            response = client.post("/reservations", json={"sku": "demo", "quantity": quantity})
            assert response.status_code == 422
        assert (
            client.post(
                "/reservations", json={"sku": "demo", "quantity": 1, "available": 100}
            ).status_code
            == 422
        )
