from typing import Annotated
from uuid import UUID

import psycopg
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from orderflow import reservations
from orderflow.db import connect
from orderflow.errors import ReservationError


class ReservationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    sku: str = Field(pattern=r"^[A-Za-z0-9_-]{1,64}$")
    quantity: int = Field(gt=0, le=2_147_483_647)


class ReservationResult(BaseModel):
    id: UUID
    sku: str
    quantity: int


app = FastAPI(title="OrderFlow")


@app.exception_handler(ReservationError)
async def rejected(request: Request, error: ReservationError):
    return JSONResponse(status_code=error.status, content={"detail": error.code})


@app.exception_handler(psycopg.Error)
async def unavailable(request: Request, error: psycopg.Error):
    return JSONResponse(status_code=503, content={"detail": "DATABASE_UNAVAILABLE"})


@app.get("/health")
def health():
    with connect() as db:
        db.execute("SELECT 1")
    return {"status": "ready"}


@app.post("/reservations", response_model=ReservationResult, status_code=201)
def create_reservation(
    request: ReservationRequest,
    idempotency_key: Annotated[str | None, Header(min_length=1, max_length=128)] = None,
):
    return reservations.reserve(request.sku, request.quantity, idempotency_key)
