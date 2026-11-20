# Synapse Assess — Browser IDE & Remote Sandbox Architecture

Technical Architecture Specification · Draft v0.1 · Assessment 001

## 1. Architecture decision

I recommend a browser-native IDE backed by an isolated, ephemeral Linux development environment, with the Synapse Assess backend acting as the control plane.

The browser handles editing, navigation, terminal presentation, AI chat, microphone capture, and assessment status. The remote sandbox owns the candidate's working files, executes commands, runs tests, and produces source-control snapshots.

The central architectural principle is:

The browser is an untrusted interface. The sandbox executes untrusted candidate code. The control plane owns assessment rules and authoritative state.

These responsibilities must remain separate.

## Recommended architecture

Logical architecture. Network connectivity between services is policy-controlled; the sandbox has no direct access to the control-plane database or privileged credentials.

## 2. Technology stack

| Layer              | Choice                                      | Responsibility                       |
| ------------------ | ------------------------------------------- | ------------------------------------ |
| Frontend           | Next.js + TypeScript                        | Candidate-facing application         |
| Code editor        | Monaco Editor                               | Editing, diagnostics, file models    |
| Terminal           | xterm.js                                    | Browser terminal interface           |
| API                | FastAPI + Pydantic                          | Control plane and session APIs       |
| Realtime transport | WebSockets                                  | Terminal, file updates, status       |
| Sandbox            | Managed microVM/container-isolated provider | Untrusted execution                  |
| Sandbox agent      | Small internal service                      | Filesystem, PTY, commands, snapshots |
| Database           | PostgreSQL                                  | Authoritative assessment state       |
| Cache/queue        | Redis + Celery                              | Background orchestration             |
| Object storage     | S3-compatible                               | Snapshots and evidence artifacts     |
| AI                 | Provider-neutral gateway                    | Controlled assistant and tool calls  |
| Transcription      | Streaming STT provider                      | Timestamped spoken reasoning         |

The sandbox provider should be replaceable through a defined adapter interface. Avoid coupling the candidate application directly to one vendor's SDK.

## 3. Browser IDE design

The IDE should feel familiar without attempting to recreate all of VS Code.

OrderFlow Assessment

Stage A · 24:18

EXPLORER

▾ app

　▾ services

　　reservation_service.py

　▸ repositories

▸ tests

reservation_service.py

12  async def reserve(...)

13    stock = await get_stock()

14    if stock >= quantity:

15      await update_stock()

16      ...

TERMINAL

bash

$ pytest tests/test_concurrency.py

1 failed, 3 passed

Reasoning capture active

AI disabled

Conceptual candidate workspace, not a functioning editor.

### IDE modules

The first version needs six modules:

1. File explorer: Browse the candidate workspace, create files, rename files, and inspect directory structure.
2. Editor: Monaco models, syntax highlighting, diagnostics, tabs, save status, and keyboard shortcuts.
3. Terminal: Interactive shell connected to a sandbox PTY.
4. Assessment panel: Instructions, stage progress, remaining time, and submission controls.
5. AI assistant: Available only in Stage B under the configured policy.
6. Reasoning capture: Microphone state, live transcript, and optional reasoning checkpoints.

The IDE should preserve unsaved edits across temporary network interruptions and show synchronization status.

### File synchronization

I recommend a server-authoritative filesystem.

Monaco holds an in-memory editing buffer. The sandbox holds the actual working files.

The browser saves through an authenticated API using file revisions or ETags to prevent stale writes from silently overwriting newer content.

Before running tests, the IDE must flush pending edits. The execution request should reference a known workspace revision.

This prevents a common failure where candidates see updated code in the editor but tests run against an older file on disk.

For MVP purposes, debounced saves plus explicit save-before-run behavior are sufficient. Real-time collaborative editing is out of scope.

## 4. Remote sandbox architecture

This is the most security-sensitive component of Synapse Assess.

The candidate can execute arbitrary Python code, install permitted dependencies, modify repository files, and invoke tests. That code must never be trusted with platform credentials or access to other candidates' environments.

### Isolation model

Trusted control plane

FastAPI, PostgreSQL, assessment policy, authentication, hidden tests, scoring rules, and cloud credentials.

Authenticated, scoped sandbox broker

Untrusted candidate sandbox

Disposable filesystem, Python runtime, terminal, application code, approved dependencies, and candidate-visible tests.

Controlled submission artifact

Trusted evaluation worker

Replays the submitted code in a fresh isolated environment, injects hidden tests, executes grading, and stores results.

### Mandatory sandbox controls

| Boundary         | Required behavior                                             |
| ---------------- | ------------------------------------------------------------- |
| Tenant isolation | Separate sandbox per assessment attempt                       |
| Privileges       | Non-root runtime, no privileged container access              |
| Resources        | CPU, memory, process, disk, and runtime quotas                |
| Network          | Deny by default; explicit allowlists when needed              |
| Secrets          | No database credentials, grading keys, or platform API tokens |
| Filesystem       | Scoped workspace and ephemeral scratch storage                |
| Lifecycle        | Time-limited, disposable, and revocable                       |
| Logging          | Resource use, execution status, and infrastructure errors     |
| Hidden tests     | Never mounted into the candidate environment                  |

A managed sandbox provider should be evaluated against these requirements. Containerization alone is not a sufficient security claim.

### Sandbox provider interface

The rest of Synapse Assess should interact with a provider-neutral interface:

```
from typing import Protocolclass SandboxProvider(Protocol):    async def create(        self, image: str, limits: dict    ) -> str: ...    async def execute(        self, sandbox_id: str, command: list[str]    ) -> dict: ...    async def snapshot(        self, sandbox_id: str    ) -> str: ...    async def destroy(        self, sandbox_id: str    ) -> None: ...
```

This is an illustrative contract. The production interface also needs file operations, terminal streams, cancellation, timeouts, idempotency, health checks, and typed error handling.

I would keep the provider implementation behind `SandboxManager`, so changing vendors does not require rewriting the frontend.

## 5. The assessment session lifecycle

The control plane owns a state machine, not a collection of unrelated timers.

Additional terminal states include canceled, expired, and failed. A reviewed session progresses to a finalized report.

### Stage transition rules

At the end of Stage A:

1. The server closes Stage A for new writes and commands.
2. Pending editor changes are synchronized, or an explicit failure is recorded.
3. The system captures an immutable Stage A snapshot.
4. The evidence log records the snapshot identifier and stage-end timestamp.
5. The control plane authorizes Stage B and enables the AI gateway.

The browser must never be able to enable AI access merely by changing client-side state.

At the end of Stage B, the system captures another snapshot and closes the candidate's execution privileges.

### Failure recovery

If a candidate loses connectivity, the authoritative timer continues according to the configured policy. The candidate should be able to reconnect to the same sandbox when possible.

If infrastructure fails, the system needs a separate policy for pausing, extending, or restarting the assessment. Infrastructure outages must not automatically be treated as candidate failures.

A session lease and reconciliation worker should identify abandoned sandboxes and clean them up.

## 6. Terminal and command execution

The browser terminal uses xterm.js, but all shell execution occurs remotely.

The communication path is:

`xterm.js → authenticated WebSocket → terminal broker → sandbox PTY`

Each terminal connection must be bound to the candidate's authorized assessment session.

The broker validates session state, sandbox ownership, and terminal permissions before attaching to the PTY.

### Important distinction

The terminal is a general-purpose shell inside an isolated environment. It should not be trusted to obey assessment rules.

A candidate could run arbitrary commands, modify local files, or attempt to access the network.

Therefore, restrictions must be enforced at the sandbox and network boundary, not merely by hiding buttons in the browser.

For Stage A, blocking AI domains is not enough to guarantee no external assistance. The platform should restrict sandbox network egress and clearly disclose the limits of remote integrity controls.

## 7. Evidence capture architecture

This is the most strategically important system after the sandbox.

I recommend a unified event schema with a server-generated sequence and timestamp.

```
from datetime import datetimefrom uuid import UUIDfrom pydantic import BaseModelclass AssessmentEvent(BaseModel):    event_id: UUID    session_id: UUID    stage_id: UUID    sequence: int    event_type: str    occurred_at: datetime    received_at: datetime    source: str    payload: dict    artifact_uri: str | None = None
```

The distinction between `occurred_at` and `received_at` matters.

Browser and sandbox events can arrive late or out of order. The system should preserve their original timing while assigning an authoritative ingestion order.

### Event categories

| Category       | Examples                                                 |
| -------------- | -------------------------------------------------------- |
| Workspace      | File opened, saved, renamed                              |
| Execution      | Command started, test completed                          |
| Source control | Diff generated, snapshot created                         |
| AI             | Prompt submitted, response returned, tool approved       |
| Reasoning      | Transcript segment finalized                             |
| Assessment     | Stage started, paused, submitted                         |
| Integrity      | Session reconnect, policy violation, environment failure |

Do not capture every keystroke by default. That creates unnecessary storage, privacy, and analysis costs.

Periodic snapshots, meaningful file operations, test events, and AI interactions should provide sufficient evidence for the first pilot.

### Event correlation

The system should use session-relative timestamps to align speech with engineering activity.

For example, a spoken explanation at 14:22 can be associated with a file edit at 14:35 and a test run at 15:01.

However, the correlation is temporal, not causal. The report should not claim that the spoken explanation caused the subsequent code change.

## 8. AI and microphone integration

Both services should connect through the control plane rather than receiving unrestricted sandbox access.

### AI gateway

Stage B should provide a controlled assistant with access to selected repository files and approved tools.

The gateway must enforce the active stage, model configuration, token budget, tool permissions, and logging policy.

Candidate-approved code changes should flow through the same workspace APIs as ordinary edits, allowing the evidence system to distinguish AI-proposed changes from candidate actions.

### Live transcription

The browser captures microphone audio after explicit consent. Audio chunks are streamed to the transcription service through an authenticated connection.

The service returns interim and finalized transcript segments. Only finalized segments should be treated as stable evidence.

The candidate should see recording and transcription status, with a clear indication of interruptions.

The system must support an approved written-reasoning alternative.

For the MVP, I recommend storing timestamped transcripts and retaining raw audio only for a short, disclosed quality-review period.

## 9. Assessment 001 deployment

OrderFlow requires PostgreSQL concurrency behavior, so its sandbox design must account for a real database.

I recommend a disposable database instance or isolated database environment associated with each assessment attempt.

The candidate should receive only credentials scoped to that disposable environment.

The hidden-test evaluator must use a separate fresh database and execution environment.

This prevents candidates from modifying the grading database, reading other submissions, or depending on accidental state left behind by previous attempts.

### Assessment package

Each assessment should have a manifest defining:

```
assessment_id: assessment-001
version: 1.0.0
runtime:
  language: python
  version: "3.12"
  database: postgresql
stages:
  - id: independent
    duration_minutes: 35
    ai_enabled: false
  - id: assisted
    duration_minutes: 40
    ai_enabled: true
  - id: defense
    duration_minutes: 15
    ai_enabled: false
evidence:
  capture_git_snapshots: true
  capture_test_results: true
  capture_reasoning_transcript: true
```

The manifest is a simplified example. A production manifest should also define resource limits, image digests, network policy, permitted tools, retention settings, and assessment artifact references.

## 10. Recommended implementation milestones

| Milestone | Deliverable                    | Acceptance condition                             |
| --------- | ------------------------------ | ------------------------------------------------ |
| M1        | OrderFlow reference assessment | Defects and solutions reproducible               |
| M2        | Sandbox provider adapter       | Provision, execute, snapshot, destroy            |
| M3        | Browser IDE                    | Files, editing, terminal, reliable saves         |
| M4        | Session state machine          | Server-enforced stages and transitions           |
| M5        | Evidence pipeline              | Ordered events and immutable snapshots           |
| M6        | AI gateway                     | Stage-specific permissions and logs              |
| M7        | Live reasoning capture         | Timestamped transcript and event alignment       |
| M8        | Reviewer interface             | Code, tests, transcript, and rubric in one view  |
| M9        | Pilot hardening                | Isolation tests, failure recovery, accessibility |

I would implement these sequentially, with end-to-end tests at each milestone.

## 11. Decisions to finalize before implementation

## Architecture decision register

Sandbox infrastructure

Managed isolated sandboxes (recommended)

Self-hosted microVM infrastructure

Candidate editor

Monaco + xterm.js (recommended)

Hosted VS Code environment

Database isolation

Disposable database per attempt (recommended)

Shared database server with isolated databases

AI integration

Provider-neutral gateway (recommended)

Single-provider direct integration

Finalize architecture decisions&#x20;

## Final technical recommendation

Build a modular control plane with an isolated execution plane and a unified evidence pipeline.

For Synapse Assess, the evidence system is not an optional analytics feature. It is the mechanism that connects code, tests, AI assistance, and spoken reasoning into a defensible technical evaluation.

I would keep the first implementation tightly scoped to Assessment 001, using Monaco, xterm.js, FastAPI, PostgreSQL, and managed isolated sandboxes.

The next technical deliverable should be an Architecture Decision Record and implementation contract covering the sandbox provider, filesystem synchronization, terminal protocol, stage transitions, event schema, and security boundaries.

That will give Codex a precise foundation for implementation without prematurely committing SynapseFaster to a complex infrastructure stack.