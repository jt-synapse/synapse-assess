import os
from uuid import uuid4

import httpx
import psycopg
import pytest


def pytest_addoption(parser):
    parser.addoption("--verify-starter-defects", action="store_true", default=False)


@pytest.fixture
def starter(request):
    return request.config.getoption("--verify-starter-defects")


@pytest.fixture
def db():
    with psycopg.connect(os.environ["EVALUATOR_DATABASE_URL"], autocommit=True) as connection:
        yield connection


@pytest.fixture
def client():
    transport = httpx.HTTPTransport(uds=os.environ["EVALUATOR_API_SOCKET"])
    with httpx.Client(transport=transport, base_url="http://orderflow", timeout=15) as api:
        yield api


@pytest.fixture
def stock(db):
    def create(quantity):
        sku = uuid4().hex
        db.execute("INSERT INTO inventory VALUES (%s, %s)", (sku, quantity))
        return sku

    return create
