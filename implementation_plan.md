# Synapse Assess — Finalized Technical Architecture

Architecture Baseline v1.1 · November 19, 2026 · SynapseFaster LLC

## Architecture status

Decisions finalized

The project baseline applies to every assessment package. The [architecture decision records](docs/architecture/trust-domains.md#architecture-decision-review) track formal status. The [shared contracts](packages/contracts/) define the machine-readable interfaces. Vendor selection and live security and performance validation remain open.

Scope: Browser IDE, remote execution, hybrid assessment orchestration, AI integration, live reasoning capture, and reviewer evidence.

## 1. Final architecture decisions

| ID      | Decision                                                           | Status            |
| ------- | ------------------------------------------------------------------ | ----------------- |
| ADR-001 | Managed isolated execution sandboxes                               | Accepted          |
| ADR-002 | Monaco Editor + xterm.js                                           | Accepted          |
| ADR-003 | Dedicated disposable PostgreSQL environment per assessment attempt | Accepted          |
| ADR-004 | Provider-neutral AI gateway                                        | Accepted          |
| ADR-005 | Modular FastAPI control plane                                      | Proposed baseline |
| ADR-006 | Append-only assessment evidence                                    | Proposed baseline |
| ADR-007 | Server-authoritative assessment state machine                      | Proposed baseline |
| ADR-008 | Streaming reasoning transcription                                  | Proposed baseline |
| ADR-009 | Separate trusted grading environment                               | Proposed baseline |
| ADR-010 | Assessment content versioning                                      | Proposed baseline |
| ADR-011 | PostgreSQL inside the managed sandbox when required by the package | Accepted          |

ADR-001 through ADR-004 and ADR-011 are accepted. ADR-005 through ADR-010 are proposed for formal ratification.

## 2. System boundaries

The architecture separates four trust domains.

The candidate execution environment must never receive platform database credentials, hidden tests, reference solutions, signing keys, or unrestricted AI provider credentials.

The dedicated assessment database is disposable and separate from the control-plane database. It is not merely a different schema in the production application database.

## 3. Component architecture

| Component                   | Technology                      | Deployment               |
| --------------------------- | ------------------------------- | ------------------------ |
| Candidate/employer frontend | Next.js, React, TypeScript      | Web application          |
| Editor                      | Monaco                          | Browser                  |
| Terminal                    | xterm.js                        | Browser                  |
| Control plane               | FastAPI, Pydantic               | Application service      |
| ORM/migrations              | SQLAlchemy, Alembic             | API + migrations         |
| State database              | PostgreSQL                      | Managed database         |
| Job orchestration           | Celery + Redis initially        | Worker                   |
| Sandbox broker              | Python adapter                  | API/worker               |
| Execution runtime           | Managed isolated sandbox        | External execution plane |
| Assessment database         | Disposable PostgreSQL           | Per attempt              |
| AI gateway                  | Provider-neutral adapter        | Trusted backend          |
| Transcription               | Managed streaming STT           | Trusted integration      |
| Artifact storage            | S3-compatible                   | Object storage           |
| Observability               | OpenTelemetry + structured logs | Shared infrastructure    |

For local development, use Docker Compose for the control-plane services. Do not treat local Docker Compose as a substitute for secure isolation of arbitrary candidate code in a public deployment.

# 4. Implementation contracts

## 4.1 API conventions

All REST endpoints use `/api/v1`.

Authentication is handled by short-lived credentials. Authorization must be checked against organization membership, assessment ownership, and active session state.

Use:

- UUIDs for externally visible resource identifiers.
- UTC timestamps in ISO 8601 format.
- Explicit request and response schemas.
- Structured error responses.
- Idempotency keys for operations that create external resources.
- Optimistic concurrency control for mutable workspace files.
- Cursor-based pagination for event and report retrieval.

A standard error envelope:

```
{
  "error": {
    "code": "STAGE_NOT_ACTIVE",
    "message": "The requested operation is not permitted.",
    "request_id": "00000000-0000-4000-8000-000000000001"
  }
}
```

Production errors must not expose internal paths, secrets, stack traces, or hidden assessment material.

## 4.2 Core REST API

The [OpenAPI inventory](packages/contracts/generated/openapi.json) defines the complete REST and WebSocket contracts, including file creation, rename and deletion, stage completion, defense answers, audio, transcript corrections, and reviewer actions. Each operation identifies its caller and implementation status. The local API serves the two health checks in M0.

| Method | Endpoint                                  | Purpose                      |
| ------ | ----------------------------------------- | ---------------------------- |
| POST   | `/api/v1/assessments/{id}/invitations`    | Invite candidate             |
| POST   | `/api/v1/sessions`                        | Create assessment session    |
| GET    | `/api/v1/sessions/{id}`                   | Retrieve authoritative state |
| POST   | `/api/v1/sessions/{id}/start`             | Begin assessment             |
| POST   | `/api/v1/sessions/{id}/submit`            | Final submission             |
| GET    | `/api/v1/sessions/{id}/workspace`         | Workspace metadata           |
| GET    | `/api/v1/sessions/{id}/files`             | List files                   |
| GET    | `/api/v1/sessions/{id}/files/content`     | Read file                    |
| PUT    | `/api/v1/sessions/{id}/files/content`     | Save file                    |
| POST   | `/api/v1/sessions/{id}/executions`        | Run approved command/test    |
| POST   | `/api/v1/sessions/{id}/terminal-tickets`  | Request terminal connection  |
| POST   | `/api/v1/sessions/{id}/ai/messages`       | AI-assisted interaction      |
| POST   | `/api/v1/sessions/{id}/reasoning/consent` | Record audio consent         |
| GET    | `/api/v1/sessions/{id}/events`            | Retrieve authorized events   |
| GET    | `/api/v1/sessions/{id}/report`            | Retrieve assessment report   |

Candidate access to events and reports must be separately authorized. Employer-only grading evidence and hidden test results must not be exposed through general candidate APIs.

## 4.3 Session state contract

The authoritative state machine is:

`CREATED → PROVISIONING → READY → STAGE_A_ACTIVE → STAGE_A_SEALING → STAGE_B_ACTIVE → STAGE_B_SEALING → DEFENSE_ACTIVE → SUBMITTED → EVALUATING → REVIEWED → FINALIZED`

Additional terminal states: `CANCELED`, `EXPIRED`, and `FAILED`.

State transitions are server-enforced and recorded transactionally.

The browser cannot set its own stage, modify remaining time, or enable AI access.

### Session response

```
{
  "session_id": "00000000-0000-4000-8000-000000000001",
  "assessment_version_id": "00000000-0000-4000-8000-000000000002",
  "server_time": "2026-11-19T14:01:00Z",
  "state": "STAGE_A_ACTIVE",
  "stage": {
    "stage_id": "independent",
    "stage_attempt_id": "00000000-0000-4000-8000-000000000003",
    "started_at": "2026-11-19T14:00:00Z",
    "deadline_at": "2026-11-19T14:35:00Z",
    "ai_enabled": false
  },
  "workspace": {
    "status": "READY",
    "revision": 17
  }
}
```

The frontend derives the visible countdown from the server deadline and reconciles against server time.

### Transition guarantees

Each transition must be idempotent and protected against concurrent requests.

Stage A sealing must capture an immutable snapshot before Stage B begins. If sealing fails, Stage B must not start.

A failed transition produces a recoverable operational state, not a silently corrupted assessment.

## 5. Workspace and filesystem contracts

The sandbox filesystem is authoritative. Monaco maintains editable buffers that synchronize with it.

### File save request

```
{
  "path": "app/services/reservation_service.py",
  "content": "updated source content",
  "expected_revision": 12,
  "client_operation_id": "uuid"
}
```

### File save response

```
{
  "path": "app/services/reservation_service.py",
  "revision": 13,
  "content_sha256": "sha256-hex",
  "saved_at": "2026-11-19T14:12:00Z"
}
```

A stale revision returns `409 WORKSPACE_REVISION_CONFLICT`.

File paths must be canonicalized and restricted to the candidate workspace. Reject traversal, unauthorized symlink resolution, and access to reserved system paths.

### Workspace revision model

I recommend a monotonic workspace revision number with per-file revisions.

A file save increments the relevant file revision and the workspace revision.

Before an execution begins, pending browser changes must be synchronized. The execution record references the workspace revision used.

For a stronger reproducibility guarantee, the execution service should create a content-addressed snapshot or lock the relevant workspace revision before running tests.

## 6. Terminal protocol

The terminal connection uses a short-lived, single-purpose ticket.

Flow:

1. Candidate requests a terminal ticket.
2. API validates session ownership and stage permissions.
3. API issues a short-lived ticket bound to the sandbox and session.
4. Browser opens the terminal WebSocket.
5. Broker validates the ticket and attaches to the sandbox PTY.
6. Broker closes the connection when the stage ends or authorization is revoked.

WebSocket endpoint:

`/api/v1/sessions/{id}/terminal/ws`

Terminal messages should use typed frames for input, output, resize, heartbeat, and close.

A terminal ticket must not grant access to another sandbox or permit arbitrary broker commands.

### Command execution

Use separate APIs for structured execution and interactive terminal access.

Structured execution is appropriate for test runs and evidence capture. Interactive terminal access supports exploration and debugging.

Both execute inside the sandbox, but structured executions produce normalized records:

```
{
  "execution_id": "uuid",
  "workspace_revision": 18,
  "command": ["pytest", "tests/test_concurrency.py"],
  "status": "COMPLETED",
  "exit_code": 0,
  "duration_ms": 1832,
  "stdout_artifact_id": "uuid",
  "stderr_artifact_id": "uuid"
}
```

Do not trust client-supplied command metadata as evidence of what actually executed. The sandbox broker must record the authoritative command and result.

## 7. Sandbox provider contract

The [provider protocol](services/execution/src/synapse_execution/provider.py) defines provisioning, health, file reads and writes, structured execution, terminal attachment, snapshot, restore, and termination. Each operation takes an owned sandbox handle or a session-scoped specification. SB-001 determines which capabilities each provider can deliver.

The adapter may need to compose provider APIs with an internal sandbox agent.

### Provisioning sequence

1. Load immutable assessment version.
2. Resolve approved runtime image by digest.
3. Create an isolated sandbox with CPU, memory, disk, process, network, and lifetime limits in force.
4. Provision the candidate-visible repository.
5. When the package declares PostgreSQL, start a dedicated disposable instance inside the sandbox.
6. For that instance, supply attempt-scoped credentials, apply migrations, and seed the database.
7. Verify filesystem confinement and effective limits.
8. Verify workspace health and readiness of any declared services.
9. Record provisioned resource identifiers.
10. Mark the session `READY`.

All resources must be tagged with the session ID and expiration deadline for cleanup.

### Cleanup

Termination must be idempotent.

A reconciliation worker periodically identifies resources that have expired, lost their owner session, or failed during provisioning.

The system must support cleanup even when the original API request was interrupted.

## 8. Dedicated database architecture

Assessment 001 requires PostgreSQL semantics for concurrency and transactional correctness.

The chosen design is a disposable in-sandbox PostgreSQL environment for each attempt whose package declares PostgreSQL.

The database must be isolated from the platform database and other candidates' databases.

### Database requirements

- Dedicated credentials per attempt.
- No superuser access for candidate code.
- No access to other assessment databases.
- Reproducible schema migrations and seed data.
- Resource and connection limits.
- Snapshot or reset capability.
- Automatic destruction after the retention window.
- Separate fresh database for hidden-test evaluation.

A dedicated database does not necessarily require a dedicated physical server. It requires an isolation model that prevents cross-attempt access and interference.

ADR-011 requires PostgreSQL to run as a supervised service within the attempt's managed sandbox. Packages without a PostgreSQL requirement omit the service.

## 9. AI gateway contract

The AI gateway is trusted infrastructure. It must not expose provider API keys to the candidate browser or sandbox.

### Request

```
{
  "session_id": "uuid",
  "stage_id": "assisted",
  "messages": [
    {
      "role": "user",
      "content": "Review the idempotency implementation."
    }
  ],
  "context": {
    "workspace_revision": 31,
    "file_paths": [
      "app/services/reservation_service.py"
    ]
  }
}
```

The server must independently resolve the active stage, permitted model, context files, and tool policy. Client-supplied values are requests, not authorization.

### Gateway responsibilities

- Validate active assessment stage.
- Select the configured provider and model.
- Enforce token and cost budgets.
- Retrieve only authorized repository context.
- Log request and response metadata.
- Record approved tool calls.
- Prevent access to hidden tests or evaluator materials.
- Handle provider failures and rate limits.
- Return normalized responses independent of provider.

For Stage A, the AI gateway must reject all candidate AI requests.

For Stage B, the gateway should initially support read-only repository context and suggested code changes. Automatic write and command execution can be added after explicit approval workflows are validated.

## 10. Live reasoning capture contract

Microphone capture is part of the candidate application, not the sandbox.

The browser requests microphone permission after displaying the recording notice and obtaining the required consent.

### Audio transport

Use an authenticated streaming connection with bounded buffering and backpressure.

The server assigns each audio segment to a session and stage. The transcription provider returns interim and final text.

Only final segments become stable transcript evidence.

### Transcript event

```
{
  "event_type": "reasoning.transcript.finalized",
  "session_id": "uuid",
  "stage_id": "independent",
  "occurred_at": "2026-11-19T14:12:42Z",
  "payload": {
    "start_ms": 762000,
    "end_ms": 768500,
    "text": "Both requests can read the same inventory value.",
    "language": "en",
    "transcription_model": "provider-model-version"
  }
}
```

The transcript must be editable only through an auditable correction mechanism. Original evidence should remain distinguishable from corrected text.

### Privacy controls

The platform must support:

- Explicit consent and recording status.
- Configurable audio retention.
- Transcript access controls.
- Candidate-visible recording interruptions.
- Authorized deletion.
- Written-reasoning alternatives.
- No scoring based on accent, speaking rate, or vocal characteristics.

# 11. Evidence and evaluation architecture

## 11.1 Event storage

Use an append-only event table with:

- Event ID
- Session ID
- Stage ID
- Server sequence
- Event type
- Source
- Occurrence timestamp
- Ingestion timestamp
- Payload schema version
- Artifact reference
- Integrity hash where appropriate

Events should be immutable after ingestion. Corrections are represented as additional events.

### Ordering

The server assigns a monotonic sequence per session.

Client timestamps are retained for correlation but are not trusted as authoritative ordering evidence.

Deduplicate retries using event IDs or client operation IDs.

### Event examples

`workspace.file.saved`, `execution.started`, `execution.completed`, `ai.message.created`, `ai.tool.approved`, `reasoning.transcript.finalized`, `assessment.stage.sealed`, and `assessment.submitted`.

## 11.2 Snapshot strategy

Capture immutable snapshots at:

- Initial workspace provisioning.
- End of Stage A.
- End of Stage B.
- Final submission.

Optional periodic recovery snapshots can be stored separately from formal assessment evidence.

Each formal snapshot should include the assessment version, workspace content hash, runtime image digest, stage identifier, and timestamp.

## 11.3 Trusted evaluation

Hidden tests run only after submission in a fresh isolated environment.

The evaluator receives a read-only submission artifact and an approved grading package.

It must not share credentials, filesystem state, or database instances with the candidate sandbox.

The evaluator produces structured results that are ingested by the trusted control plane.

Human reviewers then assess interpretive competencies using the rubric and linked evidence.

# 12. Security boundaries and threat model

| Threat                                    | Required mitigation                                         |
| ----------------------------------------- | ----------------------------------------------------------- |
| Candidate code escaping sandbox           | Managed isolation, nonprivileged execution, resource limits |
| Cross-tenant data access                  | Organization authorization and per-session isolation        |
| Hidden test disclosure                    | Separate grading artifacts and evaluator environment        |
| Prompt injection through repository files | Treat repository content as untrusted AI context            |
| AI access during Stage A                  | Server-side policy enforcement                              |
| Unauthorized terminal access              | Scoped short-lived tickets                                  |
| Workspace path traversal                  | Canonical path validation and filesystem confinement        |
| Resource exhaustion                       | CPU, memory, process, disk, and time quotas                 |
| Database interference                     | Dedicated disposable assessment database                    |
| Evidence tampering                        | Server sequencing, immutable artifacts, audit events        |
| Audio data exposure                       | Encryption, access controls, retention policies             |
| Abandoned infrastructure                  | Leases, expiration, reconciliation cleanup                  |

The architecture cannot guarantee that a remote candidate has no secondary device or external assistance.

The integrity claim must be limited to the controls actually enforced and observed.

### Security testing

Before external pilots, test:

- Cross-session authorization failures.
- Sandbox escape attempts using benign security test cases.
- Network egress restrictions.
- Secret exposure through environment variables and logs.
- Terminal ticket replay and expiration.
- Stage transition races.
- File revision conflicts.
- Hidden-test isolation.
- Audio stream interruption and deletion.
- Resource cleanup after crashes.

# 13. Implementation plan

I recommend nine milestones, with explicit exit criteria.

M0 — Repository and architecture contracts

Establish monorepo structure, development tooling, API schema conventions, ADRs, testing standards, and CI.

Exit: Reproducible local control-plane startup and contract validation.

M1 — Assessment 001 reference implementation

Build OrderFlow, seed defects, reference solutions, visible tests, hidden tests, and disposable PostgreSQL setup.

Exit: Reproducible failures and verified reference solutions.

M2 — Sandbox lifecycle

Implement provider adapter, provisioning, health checks, execution, snapshots, and cleanup.

Exit: Automated lifecycle tests and isolation validation.

M3 — Browser IDE

Build file explorer, Monaco editor, terminal, workspace synchronization, and test runner.

Exit: Candidate can edit, execute, and preserve work through reconnects.

M4 — Assessment orchestration

Implement session state machine, timers, transitions, stage policies, and snapshots.

Exit: Server-enforced transitions and recovery tests pass.

M5 — Evidence pipeline

Implement event ingestion, sequencing, artifact references, and timeline queries.

Exit: Reconstruct an assessment from stored evidence.

M6 — AI gateway

Implement provider adapter, stage enforcement, context retrieval, usage budgets, and interaction logging.

Exit: Stage A denies AI access; Stage B records authorized interactions.

M7 — Live reasoning capture

Implement consent, streaming audio, transcription, timestamp alignment, and retention controls.

Exit: Transcripts correlate with code and test events under reconnect conditions.

M8 — Evaluation and pilot readiness

Build trusted hidden-test execution, reviewer rubric, evidence report, and operational dashboards.

Exit: End-to-end pilot assessment passes reliability, security, and reviewer acceptance tests.

# 14. Architecture Decision Records

### ADR-001 — Managed isolated sandboxes

Decision: Use a managed execution provider behind a provider-neutral adapter.

Rationale: Reduces infrastructure burden and avoids building a custom isolation platform before product validation.

Consequences: Vendor cost, latency, capability constraints, and provider availability must be evaluated.

Acceptance criteria: Per-attempt isolation, resource limits, terminal support, snapshots, network controls, and reliable cleanup.

### ADR-002 — Monaco + xterm.js

Decision: Build a browser-native IDE using Monaco and xterm.js.

Rationale: Provides a familiar editing and terminal experience without operating a complete hosted VS Code environment.

Consequences: File synchronization, language tooling, and terminal integration remain platform responsibilities.

Acceptance criteria: Reliable saves, multi-file editing, terminal execution, reconnect recovery, and accessibility testing.

### ADR-003 — Dedicated disposable PostgreSQL

Decision: Provision a separate disposable PostgreSQL instance inside each managed sandbox whose assessment declares the service, as specified by ADR-011.

Rationale: Preserves concurrency semantics while isolating candidate data and preventing cross-attempt contamination.

Consequences: Higher provisioning complexity and resource cost.

Acceptance criteria: Isolation, deterministic seeding, scoped credentials, reliable reset, and automatic cleanup.

### ADR-004 — Provider-neutral AI gateway

Decision: Route candidate AI interactions through a backend abstraction.

Rationale: Enables policy enforcement, model changes, usage metering, and evidence collection.

Consequences: Additional integration complexity and responsibility for prompt/tool security.

Acceptance criteria: Stage enforcement, provider substitution, auditable tool calls, and budget limits.

### ADR-005 — Modular FastAPI control plane

Decision: Use a modular monolith for assessment orchestration and business APIs.

Rationale: Minimizes operational complexity while preserving clear internal module boundaries.

Consequences: Requires disciplined package boundaries and dependency management.

### ADR-006 — Append-only evidence

Decision: Preserve meaningful assessment activity as immutable, versioned events.

Rationale: Supports reviewer traceability and reproducible reports.

Consequences: Requires retention management, event schema evolution, and privacy controls.

### ADR-007 — Server-authoritative state machine

Decision: All assessment stages and permissions are controlled by backend state.

Rationale: Prevents client-side manipulation of assessment rules.

Consequences: Requires transactional transitions and robust failure recovery.

### ADR-008 — Streaming reasoning transcription

Decision: Capture consented microphone audio and generate timestamped transcripts linked to assessment events.

Rationale: Provides additional evidence of technical reasoning.

Consequences: Privacy, accessibility, transcription accuracy, and operational cost requirements.

### ADR-009 — Separate trusted grading

Decision: Execute hidden tests in fresh isolated evaluation environments.

Rationale: Prevents candidate access to grading materials and avoids contaminated execution state.

Consequences: Additional compute cost and artifact transfer requirements.

### ADR-010 — Immutable assessment versions

Decision: Every session references a fixed assessment package, rubric, runtime image, and AI policy.

Rationale: Enables reproducibility, calibration, and interpretation of historical results.

Consequences: Requires explicit version publishing and migration policies.

## 15. Open engineering decisions

The architecture is sufficiently defined to begin implementation planning, but several choices should remain open until tested.

| Open decision           | Recommendation                                   |
| ----------------------- | ------------------------------------------------ |
| Managed sandbox vendor  | Benchmark at least two providers                 |
| Streaming STT vendor    | Compare latency, accuracy, cost, retention terms |
| AI provider             | Start with one model behind the gateway          |
| Sandbox image           | Pin by digest and version                        |
| Session recovery policy | Define pause/extension rules before pilots       |
| Evidence retention      | Establish employer and candidate policies        |
| Reviewer workflow       | Begin with manual human review                   |
| Production hosting      | Select after measuring prototype resource needs  |

I would avoid choosing vendors based only on advertised features. The evaluation should include real OrderFlow workloads, terminal latency, PostgreSQL provisioning, isolation guarantees, and total cost per completed assessment.

## Final architecture recommendation

The architecture is ready to serve as the implementation baseline for Synapse Assess Assessment 001.

The highest-priority engineering work is now:

1. Implement the OrderFlow reference repository and validate its defects.
2. Benchmark managed sandbox providers against the actual workload.
3. Establish the control-plane session and workspace contracts.
4. Build the minimal browser IDE.
5. Integrate evidence capture, AI assistance, and reasoning transcription.

The key technical risk is not rendering Monaco or connecting a terminal. It is maintaining trustworthy assessment state and evidence while executing arbitrary candidate code in isolated environments.

### Verification gates

1. Sandbox provider selection: Benchmark providers using the actual OrderFlow workload, including interactive terminal access, PostgreSQL concurrency tests, snapshot recovery, and isolation guarantees.
2. Execution consistency: Ensure every test run uses the intended workspace revision, and that Stage A is immutably sealed before Stage B begins.
3. Assessment integrity: Separate candidate execution, hidden-test evaluation, and evidence storage into independently enforced security boundaries.

I recommend making M0 — Repository and Architecture Contracts the next implementation milestone, followed by the executable OrderFlow assessment.

The first objective should be a working vertical slice: provision a sandbox, open a Python file in Monaco, modify it, execute a test, and persist the resulting evidence. Once that works reliably, we can add assessment stages, AI assistance, and microphone transcription.
