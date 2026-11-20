from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from synapse_contracts import ErrorDetail, ErrorEnvelope, Liveness, Readiness

from .health import Dependencies


def create_app(connect: Callable[[], Dependencies] = Dependencies.from_environment) -> FastAPI:
    deps: Dependencies

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        nonlocal deps
        deps = connect()
        try:
            yield
        finally:
            deps.close()

    app = FastAPI(title="Synapse Assess control plane", version="0.1.0", lifespan=lifespan)

    @app.get("/api/v1/health/live", response_model=Liveness, operation_id="liveness")
    def live() -> Liveness:
        return Liveness(status="alive")

    @app.get(
        "/api/v1/health/ready",
        response_model=Readiness,
        operation_id="readiness",
        responses={503: {"model": ErrorEnvelope}},
    )
    def ready() -> Readiness | JSONResponse:
        if deps.ready():
            return Readiness(status="ready")
        error = ErrorDetail(
            code="DEPENDENCY_UNAVAILABLE",
            message="Control plane dependencies are unavailable.",
            request_id=uuid4(),
        )
        return JSONResponse(
            status_code=503, content=ErrorEnvelope(error=error).model_dump(mode="json")
        )

    return app


app = create_app()
