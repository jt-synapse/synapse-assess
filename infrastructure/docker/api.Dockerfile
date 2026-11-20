FROM ghcr.io/astral-sh/uv:0.12.19 AS uv
FROM python:3.12.15-slim
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /platform
COPY pyproject.toml uv.lock ./
COPY packages/contracts/pyproject.toml packages/contracts/pyproject.toml
COPY packages/contracts/src packages/contracts/src
COPY services/execution/pyproject.toml services/execution/pyproject.toml
COPY services/execution/src services/execution/src
COPY apps/api apps/api
RUN uv sync --frozen --no-dev --package synapse-api --no-editable
ENV PATH="/platform/.venv/bin:${PATH}"
USER 65532:65532
CMD ["uvicorn", "synapse_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
