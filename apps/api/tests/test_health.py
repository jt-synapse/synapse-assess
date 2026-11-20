from unittest.mock import MagicMock, Mock
from uuid import UUID

from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from sqlalchemy.exc import OperationalError
from synapse_api.health import Dependencies
from synapse_api.main import create_app


def test_health_reads_both_dependencies_and_closes_clients():
    database, redis = MagicMock(), Mock()
    connection = database.connect.return_value.__enter__.return_value
    with TestClient(create_app(lambda: Dependencies(database, redis))) as client:
        assert client.get("/api/v1/health/live").json() == {"status": "alive"}
        database.connect.assert_not_called()
        assert client.get("/api/v1/health/ready").json() == {"status": "ready"}
        connection.execute.assert_called_once()
        redis.ping.assert_called_once()
    database.dispose.assert_called_once()
    redis.close.assert_called_once()


def test_missing_database_is_redacted_and_liveness_is_independent():
    database, redis = Mock(), Mock()
    database.connect.side_effect = OperationalError("secret", None, Exception("secret"))
    with TestClient(create_app(lambda: Dependencies(database, redis))) as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 503
        error = response.json()["error"]
        assert error["code"] == "DEPENDENCY_UNAVAILABLE"
        assert UUID(error["request_id"])
        assert "secret" not in response.text
        assert client.get("/api/v1/health/live").status_code == 200


def test_missing_redis_prevents_readiness():
    database, redis = MagicMock(), Mock()
    redis.ping.side_effect = RedisConnectionError("offline")
    assert not Dependencies(database, redis).ready()


def test_future_contract_routes_are_not_exposed():
    with TestClient(create_app(lambda: Dependencies(Mock(), Mock()))) as client:
        assert client.get("/api/v1/sessions").status_code == 404
