.PHONY: up down install contracts verify smoke
up:
	docker compose up --build --detach --wait

down:
	docker compose down

install:
	uv sync --locked --all-packages
	pnpm install --frozen-lockfile

contracts:
	uv run --locked python -m synapse_contracts.generate --check

verify: install contracts
	uv run --locked ruff check apps/api packages/contracts services/execution benchmarks
	uv run --locked mypy
	uv run --locked python -m pytest
	uv run --locked python -m unittest discover -s benchmarks/sb001/workloads/tests
	uv run --locked python -m unittest discover -s assessments/001-orderflow/tests -p test_package.py
	pnpm --filter @synapse/contracts typecheck
	pnpm --filter @synapse/web lint
	pnpm --filter @synapse/web typecheck
	pnpm --filter @synapse/web test
	pnpm --filter @synapse/web build
	docker compose config --quiet

smoke:
	bash infrastructure/docker/smoke.sh
