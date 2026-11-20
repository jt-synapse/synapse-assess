# Synapse Assess

Synapse Assess is an evidence-based engineering assessment platform. This checkout contains the local control-plane foundation, the OrderFlow reference package, shared contracts, and tools for benchmarking managed execution.

## Run the local control plane

Install Docker with Compose v2 or later. From the repository root run:

```sh
make up
```

Open [the status page](http://localhost:3000). It queries FastAPI on every request. [Liveness](http://localhost:8000/api/v1/health/live) tracks the API process. [Readiness](http://localhost:8000/api/v1/health/ready) checks the migrated platform database and Redis. The first startup builds the images and runs Alembic. Stop the services with `make down` to preserve the local platform database volume.

Only the web and API ports are published, on loopback. Use `WEB_PORT` and `API_PORT` to override host ports. The Compose credentials are for local development.

## Verify a checkout

Use the Python and Node versions in `.python-version` and `.node-version`, uv 0.12.19, and the pnpm version in `package.json`. Run:

```sh
make verify
make smoke
```

`make verify` installs locked dependencies, checks generated contracts, runs Python and TypeScript checks and tests, builds the web application, and validates the Compose configuration. `make smoke` starts a disposable Compose project and verifies the web-to-API connection, database loss, recovery, and persisted data. It removes the test project's containers and volumes on exit.

The [verification workflow](.github/workflows/verify.yml) also runs OrderFlow's project-authored starter and Stage A/B references against a fresh PostgreSQL 16 cluster. The test runner creates its own cluster and uses independent database connections. Its candidate archive is built from an explicit file list. See the [assessment package](assessments/001-orderflow/) for local authoring commands and stage-specific materials.

## What runs today

| Component | Entry point and current behavior |
| --- | --- |
| Control plane | The FastAPI application serves health checks. Its runtime OpenAPI describes the routes actually served. |
| Web | The Next.js status page reports the live readiness response and handles dependency outages. |
| Contracts | Pydantic definitions generate JSON Schema, TypeScript declarations and a [design-time API inventory](packages/contracts/generated/openapi.json). Use `x-availability` to distinguish served operations from future ones. |
| OrderFlow | The [package manifest](assessments/001-orderflow/manifest.yaml) declares the runtime, PostgreSQL requirement, stage instructions and separate artifact locations. Publishing requires verified artifact and image digests. |
| Execution | The [provider protocol](services/execution/src/synapse_execution/provider.py) defines the managed sandbox boundary. The in-memory implementation in the test suite returns fixtures. |
| Benchmark | [SB-001](benchmarks/sb001/README.md) runs against synthetic workloads using approved provider accounts and reports lifecycle measurements. Provider selection requires the full security, recovery and cost evidence. |

The browser IDE, live assessment sessions, evidence timeline, AI gateway, transcription and reviewer reporting are subsequent milestones. Observed results and open gates are recorded in the [verification record](docs/verification.md). See the [implementation plan](implementation_plan.md#13-implementation-plan) for acceptance criteria and [trust domains and data flow](docs/architecture/trust-domains.md) for ownership.
