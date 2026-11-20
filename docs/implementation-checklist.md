# Synapse Assess — MVP Implementation Checklist

> **Architecture Baseline:** v1.1 (`AGENTS.md`, `implementation_plan.md`, `ADR-001`–`ADR-011`)  
> **Last Updated:** 2026-11-20  
> **Legend:** `[x]` Implemented & Empirically Verified · `[-]` Implemented / Pending Gate or Sign-Off · `[ ]` Not Started

---

## 1. Milestone Progress Dashboard

| Milestone | Scope | Status | Verified Progress | Next Action / Gate |
|---|---|---|---|---|
| **M0** | Repository foundation & architecture contracts | `[-]` **95% (Pending sign-off)** | Monorepo, contracts, codegen, ADRs, Docker Compose, CI, and live `localhost:3000` + `make smoke` verified | Ratify `ADR-005`–`ADR-010` & create initial Git commit |
| **M1** | Assessment 001 (OrderFlow) reference package | `[x]` **Code & DB Verified** | Starter defects A1/A2, Stage A/B references, hidden probes, restart recovery & disjoint packaging verified on PostgreSQL 16 | Human pilot calibration in **M8** |
| **M2** | Managed sandbox integration | `[-]` **Prep Verified / Live Open** | `SandboxProvider` protocol, `FixtureProvider`, SB-001 harness, and synthetic Docker workloads verified locally | Run live **SB-001** (E2B vs. Daytona), ratify `ADR-012`, build production adapter |
| **M3** | Browser IDE & vertical slice | `[ ]` Not started | Wire contracts (`files`, `executions`, `terminal/ws`) defined in M0 | Implement file sync, Monaco, xterm.js, ticketed PTY broker & test runner |
| **M4** | Assessment orchestration & lifecycle | `[ ]` Not started | `SessionState` contract & sealing rules defined in M0 | Implement DB models, auth/RBAC, state machine, timers & Stage A/B sealing |
| **M5** | Append-only evidence pipeline | `[ ]` Not started | `EvidenceEvent` & `Snapshot` contracts defined in M0 | Implement event store, `server_sequence`, S3 artifacts & timeline API |
| **M6** | Trusted AI gateway | `[ ]` Not started | `AIRequest` / `AIReply` contracts defined in M0 | Implement provider adapter, Stage A block, context scoping, budgets & UI |
| **M7** | Live reasoning capture & transcription | `[ ]` Not started | Consent, discriminated audio WS frames & correction contracts defined in M0 | Implement consent UI, audio WS, streaming STT, alignment & retention |
| **M8** | Trusted evaluation, rubric & pilot readiness | `[ ]` Not started | OrderFlow hidden tests/rubric (M1) + SEC-010 `Report` contract (M0) ready | Build isolated grader worker, reviewer UI, report, security audit & pilot |

---

## 2. Architecture, Vendor & Policy Decision Register

### 2.1 Architecture Decision Records (`docs/decisions/`)
- [x] [ADR-001](decisions/ADR-001.md) — Managed execution sandboxes *(Accepted)*
- [x] [ADR-002](decisions/ADR-002.md) — Browser IDE with Monaco Editor and xterm.js *(Accepted)*
- [x] [ADR-003](decisions/ADR-003.md) — Dedicated disposable assessment databases *(Accepted)*
- [x] [ADR-004](decisions/ADR-004.md) — Provider-neutral AI gateway *(Accepted)*
- [x] [ADR-011](decisions/ADR-011.md) — Conditional PostgreSQL inside the managed sandbox *(Accepted)*
- [ ] [ADR-005](decisions/ADR-005.md) — Modular FastAPI control plane *(Authored — awaiting formal ratification)*
- [ ] [ADR-006](decisions/ADR-006.md) — Append-only assessment evidence *(Authored — awaiting formal ratification)*
- [ ] [ADR-007](decisions/ADR-007.md) — Server-authoritative session lifecycle *(Authored — awaiting formal ratification)*
- [ ] [ADR-008](decisions/ADR-008.md) — Consented reasoning transcription *(Authored — awaiting formal ratification)*
- [ ] [ADR-009](decisions/ADR-009.md) — Separate trusted grading *(Authored — awaiting formal ratification)*
- [ ] [ADR-010](decisions/ADR-010.md) — Immutable assessment versions *(Authored — awaiting formal ratification)*
- [ ] `ADR-012` — Managed sandbox provider selection (E2B vs. Daytona) *(Pending live SB-001 measurements in M2)*

### 2.2 Open Engineering & Policy Decisions (`remaining_decisions.md`)
- [ ] **P0 — Managed Sandbox Provider (M2):** Execute SB-001 and select E2B or Daytona.
- [ ] **P0 — Session Infrastructure Recovery Policy (M4):** Finalize pause/extension/restore rules for confirmed provider outages vs. candidate disconnects.
- [ ] **P0 — Initial AI Model & Provider (M6):** Select single hosted model + pinned version behind the AI gateway and define per-stage token/USD caps.
- [ ] **P1 — Authentication & RBAC (M4):** Finalize short-lived candidate session tokens and OIDC/organization RBAC for employers and reviewers.
- [ ] **P1 — Streaming STT Provider (M7):** Select speech-to-text vendor based on streaming latency, accuracy, cost, and zero-training/retention terms.
- [ ] **P1 — Evidence & Audio Retention Policy (M7/M8):** Define raw-audio quality-review retention window, transcript/report retention window, and deletion SLA.
- [ ] **P1 — Production Cloud Hosting Target (M8):** Select deployment target for control plane, PostgreSQL, Redis, workers, and S3-compatible storage after measuring prototype usage.

### 2.3 Optional Codex Project Skills (`.agents/skills/` per `skill_doc.md`)
- [ ] `architecture-governance` (P0)
- [ ] `secure-sandbox-engineering` (P0)
- [ ] `assessment-engineering` (P0)
- [ ] `fullstack-feature-delivery` (P0)
- [ ] `evidence-event-engineering` (P0)
- [ ] `ai-gateway-engineering`, `realtime-audio-engineering`, `security-review` (P1, introduce at M6–M8)

---

## 3. Milestone-by-Milestone Task Breakdown

### M0 — Repository Foundation & Architecture Contracts
- [x] Initialize workspace layout (`uv` Python 3.12 workspace + `pnpm` TypeScript workspace, [Makefile](../Makefile), [pyproject.toml](../pyproject.toml), [package.json](../package.json)).
- [x] Establish engineering governance ([AGENTS.md](../AGENTS.md), [GEMINI.md](../GEMINI.md), [trust-domains.md](architecture/trust-domains.md), `ADR-001`–`ADR-011`).
- [x] Implement canonical `/api/v1` Pydantic contracts and endpoint/WebSocket catalog in [models.py](../packages/contracts/src/synapse_contracts/models.py) and [catalog.py](../packages/contracts/src/synapse_contracts/catalog.py) (including stage transitions, file CRUD, audio discriminated frames + `is_final`, reviewer rubric, and **SEC-010** finalized report `limitations`).
- [x] Deterministic OpenAPI 3.1, JSON Schema, and TypeScript `.d.ts` code generation (`synapse_contracts.generate`) verified by Python and strict TypeScript consumer tests.
- [x] Implement control-plane health/readiness endpoints ([apps/api](../apps/api/src/synapse_api/main.py)) with redacted `503` error envelopes and initial Alembic migration (`0001_assessment_versions`).
- [x] Implement Next.js system status page ([apps/web](../apps/web/app/page.tsx)) querying live control-plane readiness.
- [x] Configure local Docker Compose ([compose.yaml](../compose.yaml), non-root `api.Dockerfile` & `web.Dockerfile`) and GitHub Actions CI ([verify.yml](../.github/workflows/verify.yml)).
- [x] **Verified Exit Check:** `make verify` checks, live `localhost:3000` browser check, and disposable `make smoke` (boot, migrate, DB stop `503`, recovery, teardown) passed ([verification.md](verification.md)).
- [ ] **Remaining to Close M0:**
  - [ ] Formally ratify `ADR-005`–`ADR-010` (mark *Accepted* with date).
  - [ ] Create initial Git commit on `main` for the verified M0+M1 baseline.
  - [ ] *(Optional cleanup)* Deduplicate repeated SB-001 section in [remaining_decisions.md](../remaining_decisions.md) and tidy formatting nits in [implementation_plan.md](../implementation_plan.md).

---

### M1 — Assessment 001 Reference Implementation (OrderFlow)
- [x] Author [manifest.yaml](../assessments/001-orderflow/manifest.yaml) (35m `independent` AI-off, 40m `assisted` AI-on, 15m `defense` AI-off, `postgresql` service, disjoint candidate/evaluator paths).
- [x] Build candidate starter ([assessments/001-orderflow/candidate](../assessments/001-orderflow/candidate/README.md)) with FastAPI, `psycopg`, numbered SQL migration, seed data (`DEMO-BOOK`, `DEMO-LAST`), hash-locked `requirements.txt`, API contract, and visible tests.
- [x] Seed deterministic Stage A defects in [reservations.py](../assessments/001-orderflow/candidate/orderflow/reservations.py):
  - [x] **Defect A1:** Non-atomic read-check-write stock allocation allowing concurrent over-reservation.
  - [x] **Defect A2:** Split early `db.commit()` leaving orphaned reservations when inventory update fails.
- [x] Author unambiguous Stage B brief ([assisted.md](../assessments/001-orderflow/instructions/assisted.md)) specifying `Idempotency-Key` scoping, payload equivalence, concurrent wait/replay, `409 IDEMPOTENCY_CONFLICT`, and key release on `422`/`404`/`409`/`503`, plus Stage C [defense.md](../assessments/001-orderflow/instructions/defense.md).
- [x] Build strictly separated evaluator materials ([assessments/001-orderflow/evaluator](../assessments/001-orderflow/evaluator/review.md)): Stage A & Stage B reference solutions, anchored 1–5 reviewer rubric + calibration guide, and hidden black-box probes (`test_independent.py`, `test_assisted.py`, driver-agnostic `pid <> pg_backend_pid()` race probe).
- [x] Build deterministic tar/release packager ([package.py](../assessments/001-orderflow/tests/package.py)) enforcing ordinary-file allowlists, symlink rejection, and SHA-256 digests.
- [x] **Verified Exit Check:** Real PostgreSQL 16 acceptance suite ([verify.py](../assessments/001-orderflow/tests/verify.py)) passed across `starter` (reproduces A1 & A2), `stage_a` reference, and `stage_b` reference (including committed retry across full API process restart).

---

### M2 — Managed Sandbox Integration
- [x] Define provider-neutral `SandboxProvider` protocol, `SandboxSpec` (deny-by-default egress, resource limits, lease expiry), string-ID `SandboxHandle`, workspace file CRUD, `Checkpoint` kinds (`workspace`, `database_consistent`, `stage_source`), and typed errors in [provider.py](../services/execution/src/synapse_execution/provider.py).
- [x] Build test-only `FixtureProvider` ([fixture_provider.py](../services/execution/tests/support/fixture_provider.py)) excluded from production package installation.
- [x] Build SB-001 benchmark suite ([benchmarks/sb001](../benchmarks/sb001/README.md)): pinned E2B & Daytona drivers, crash-safe journal & orphan reconciler, 110-minute raw-PTY probe, P50/P95/max latency reporter, and reconciled USD cost calculator.
- [x] Build & locally verify pinned `minimal` and `orderflow` OCI workloads ([verify-images.sh](../benchmarks/sb001/workloads/verify-images.sh)): non-root `postgres` supervisor + `candidate` account, `git-core` workflow, DB restart recovery, logical `pg_dump`/`pg_restore` during active writes, and peer-auth privilege rejection.
- [ ] **Remaining for M2 Completion:**
  - [ ] Obtain human approval for E2B & Daytona benchmark accounts/spend (`AGENTS.md` §18).
  - [ ] Publish pinned `minimal` and `orderflow` templates/snapshots to E2B and Daytona; verify Daytona `os_user="candidate"` does not override `USER postgres` supervisor PID 1.
  - [ ] Run live **SB-001** benchmarks on E2B and Daytona:
    - [ ] Test Group A: 30 cold + 30 warm starts per profile (P95 ≤ 30s cold / ≤ 10s warm, termination P95 ≤ 30s).
    - [ ] Test Group B: In-sandbox PostgreSQL concurrency, app/DB restarts, and interrupted-transaction checkpoint recovery.
    - [ ] Test Group C: Interactive PTY connect (P95 ≤ 2s), keystroke echo (P95 ≤ 150ms), zero output loss, reconnect (P95 ≤ 5s), and ≥110-minute uninterrupted session longevity.
    - [ ] Test Groups D & E: Save → Execute → Verify workspace consistency and snapshot creation/restore timings.
    - [ ] Test Group F (Mandatory Pass/Fail Security Gate): Cross-sandbox fs/network denial, zero platform secret exposure, outbound egress block, privilege & CPU/RAM/PID exhaustion containment, lease expiration revocation (`SEC-001`, `SEC-002`, `SEC-006`, `SEC-007`, `SEC-008`).
    - [ ] Test Group G & Cost: Load progression (1 → 5 → 10 → 25 concurrent sessions) and reconciled billing check (target ≤ $5/completed assessment).
  - [ ] Record provider scorecard and ratify `ADR-012` (Managed Sandbox Provider Selection).
  - [ ] Implement production `SandboxProvider` adapter and `SandboxManager` in `services/execution` (including windowed PostgreSQL supervisor restart policy, session/lease tagging, and strict path confinement).
  - [ ] Implement background reconciliation worker (`Celery` + `Redis`) to reclaim expired, orphaned, or failed-provision sandboxes idempotently.
  - [ ] **M2 Exit Gate:** Automated lifecycle, PostgreSQL recovery, orphan-reconciliation, and negative isolation tests pass against the selected managed sandbox provider.

---

### M3 — Browser IDE & Vertical Slice
- [ ] **Backend Workspace & Execution (`apps/api` + `services/execution`):**
  - [ ] Implement workspace routes: `GET /workspace`, `GET /files`, `GET /files/content`, `PUT /files/content`, `POST /files`, `POST /files/rename`, `DELETE /files`.
  - [ ] Enforce canonical workspace path confinement (`SEC-008`: reject `..`, absolute paths, symlink escapes, reserved paths) inside the broker/sandbox boundary.
  - [ ] Enforce per-file and monotonic workspace revisions; return `409 WORKSPACE_REVISION_CONFLICT` on stale writes and support idempotent retries via `client_operation_id`.
  - [ ] Implement structured command execution (`POST /executions`) bound to approved assessment commands and synchronized `workspace_revision`, storing stdout/stderr in S3-compatible storage and recording broker-observed exit codes/timings (`SEC-001`).
  - [ ] Implement terminal ticket issuance (`POST /terminal-tickets`) and authenticated WebSocket PTY broker (`WS /terminal/ws`) with short-lived, single-use, session-and-sandbox-scoped tickets, origin validation, typed frames, and server-initiated revocation.
- [ ] **Frontend Candidate Workspace (`apps/web`):**
  - [ ] Build IDE layout (Tailwind CSS + `shadcn/ui`): file explorer, tabbed Monaco editor, xterm.js terminal pane, test runner panel, instructions drawer, and stage/timer header.
  - [ ] Implement revision-aware debounced autosave + explicit save (`Cmd/Ctrl+S`), save-state indicator, and `409` conflict resolution flow (never silently overwrite newer server/terminal changes).
  - [ ] Preserve dirty local buffers across temporary network drops and reconcile on reconnect.
  - [ ] Implement save-before-run test execution flow guaranteeing tests run against the exact `workspace_revision` shown in the editor.
  - [ ] Integrate xterm.js WebSocket client (resize, `Ctrl+C`, heartbeat, clean reconnect, and read-only/closed state on revocation).
- [ ] **M3 Security & Negative Tests:**
  - [ ] Path traversal, symlink escape, and binary/oversize abuse rejected.
  - [ ] Concurrent terminal + editor edits trigger `409` safely without data loss.
  - [ ] Replayed, expired, and cross-session terminal tickets rejected (`401`/`403`).
  - [ ] Keyboard navigation and baseline accessibility checks pass.
- [ ] **M3 Exit Gate:** End-to-end vertical slice (`Launch → Provision sandbox → Open OrderFlow in Monaco → Edit → Run pytest → Persist result → Survive disconnect/reconnect`) verified.

---

### M4 — Assessment Orchestration & Lifecycle
- [ ] **Persistence & Tenancy (`apps/api`):**
  - [ ] Create SQLAlchemy models & Alembic migrations for `organizations`, `users`, `memberships`, `candidates`, `assessment_invitations`, `assessment_sessions`, `stage_attempts`, and `workspace_snapshots`.
  - [ ] Implement authentication and organization/session authorization checks on every endpoint (`SEC-005`).
  - [ ] Implement `POST /assessments/{id}/invitations`, `POST /sessions`, `GET /sessions/{id}`, `POST /sessions/{id}/start`, `POST /sessions/{id}/stages/complete`, `POST /sessions/{id}/defense/answers`, and `POST /sessions/{id}/submit`.
- [ ] **Authoritative State Machine & Timers:**
  - [ ] Enforce exact state transitions (`CREATED → PROVISIONING → READY → STAGE_A_ACTIVE → STAGE_A_SEALING → STAGE_B_ACTIVE → STAGE_B_SEALING → DEFENSE_ACTIVE → SUBMITTED → EVALUATING → REVIEWED → FINALIZED` + `CANCELED`, `EXPIRED`, `FAILED`) transactionally with row locking.
  - [ ] Implement server-authoritative deadlines + Celery scheduled expiration tasks (frontend derives visible countdown from `server_time` and `deadline_at`).
  - [ ] Gate stage-specific instructions (`assisted.md` unlocked only in `STAGE_B_ACTIVE`; `defense.md` unlocked only in `DEFENSE_ACTIVE`).
- [ ] **Stage Sealing & Recovery:**
  - [ ] Implement `STAGE_A_SEALING` and `STAGE_B_SEALING`: block new mutations/executions, revoke PTY connections, flush accepted writes, capture & verify immutable `stage_source` snapshot (and DB-consistent checkpoint where required), and refuse to advance if sealing fails.
  - [ ] Implement distinct recovery workflows for candidate disconnect (timer runs, reconnect to existing sandbox) vs. confirmed infrastructure failure (pause/recover/restore from checkpoint per approved policy).
- [ ] **M4 Exit Gate:** Concurrent manual-complete vs. timer-expiry race tests, worker retry idempotency tests, client state-tampering rejection tests, and sealing-failure blocking tests pass.

---

### M5 — Append-Only Evidence Pipeline
- [ ] Create append-only `evidence_events` and `artifacts` tables + S3-compatible object storage integration with SHA-256 content verification (`SEC-009`).
- [ ] Enforce database-level append-only immutability (no silent `UPDATE`/`DELETE` on historical events; corrections appended as new referencing events).
- [ ] Implement transactional per-session monotonic `server_sequence` allocation, dual timestamps (`occurred_at` and authoritative `received_at`), `schema_version`, and `deduplication_id` idempotency.
- [ ] Capture formal immutable snapshots (`initial`, Stage A `stage_seal`, Stage B `stage_seal`, `submission`) binding `assessment_version_id`, `workspace_revision`, `source_sha256`, and `image_digest`.
- [ ] Instrument all producers: workspace file operations, structured executions, stage transitions, snapshots, environment/integrity events, and sensitive-access audit logs.
- [ ] Implement `GET /sessions/{id}/events` with opaque cursor pagination and pre-pagination caller visibility filtering (candidates never receive evaluator/reviewer events).
- [ ] **M5 Exit Gate:** Concurrent out-of-order/retried ingestion preserves strict monotonic `server_sequence`; complete candidate session can be reconstructed from stored events and snapshots; cross-role visibility leaks are blocked.

---

### M6 — Trusted AI Gateway
- [ ] Implement provider-neutral AI gateway in `services/intelligence` (`ADR-004`) with server-held credentials (`SEC-002`) and version-pinned model configuration.
- [ ] Enforce server-side stage authorization on `POST /sessions/{id}/ai/messages` (`SEC-005`): unconditionally reject requests during `STAGE_A_ACTIVE`, sealing, `DEFENSE_ACTIVE`, and non-active states.
- [ ] Implement scoped repository context loader fetching requested `file_paths` at `workspace_revision` strictly from the candidate workspace (never hidden tests, reference solutions, or secrets — `SEC-004`).
- [ ] Harden prompt construction to treat repository files and user messages as untrusted input (preventing prompt injection from overriding system instructions or tool boundaries).
- [ ] Restrict MVP AI capabilities to read-only repository context and suggested code changes/tests requiring explicit candidate acceptance through normal revision-checked workspace APIs.
- [ ] Enforce atomic per-session/per-stage token, rate, and USD cost budgets, plus normalized error/rate-limit handling.
- [ ] Emit structured evidence events (`ai.message.created`, `ai.response.completed`, `ai.suggestion.applied`) and build the Stage B AI assistant panel in `apps/web` (visibly disabled in Stage A & Defense).
- [ ] **M6 Exit Gate:** Direct API calls during Stage A fail with `403`; prompt-injection fixtures, unauthorized file-path requests, budget-race tests, and provider outage fallbacks pass.

---

### M7 — Live Reasoning Capture & Transcription
- [ ] Implement explicit recording disclosure & consent UI + `POST /sessions/{id}/reasoning/consent` (`ADR-008`); never access microphone prior to granted consent.
- [ ] Implement authenticated audio streaming endpoint (`WS /sessions/{id}/reasoning/audio/ws`) verifying origin, active session/stage, and unrevoked consent, with bounded buffers, `AudioAck` backpressure, and `(stream_id, sequence)` deduplication.
- [ ] Implement streaming STT adapter in `services/transcription` forwarding interim (`is_final=false`) segments to the UI and persisting only finalized (`is_final=true`) `reasoning.transcript.finalized` events with session-relative `start_ms`/`end_ms`.
- [ ] Build candidate reasoning UI in `apps/web`:
  - [ ] Always-visible recording & transcription status indicator + clear interruption alerts.
  - [ ] Non-blocking reasoning checkpoint prompts (initial investigation, root-cause hypothesis, implementation decision, AI evaluation, validation).
  - [ ] First-class written-reasoning input (`POST /sessions/{id}/reasoning/written`) usable at any time or as an accommodation.
- [ ] Implement auditable transcript correction (`POST /sessions/{id}/reasoning/transcripts/{segment_id}/corrections`) preserving original transcript text alongside corrections (`SEC-009`).
- [ ] Implement policy-driven raw-audio & transcript retention and auditable authorized deletion.
- [ ] **M7 Exit Gate:** Mic denial, mid-session revocation, and network drops degrade cleanly without invalidating the assessment; reconnects produce zero duplicate/misordered final segments; zero scoring on accent, speaking speed, or vocal characteristics.

---

### M8 — Trusted Evaluation, Reviewer Rubric & Pilot Readiness
- [ ] **Trusted Evaluation Plane (`ADR-009`, `SEC-004`):**
  - [ ] Implement isolated grading worker that provisions a fresh sandbox + fresh PostgreSQL instance per sealed artifact, mounts candidate source read-only alongside private `evaluator.tar`, runs Stage A and Stage B hidden suites independently, and ingests results via trusted control-plane channel.
  - [ ] Distinguish environmental/evaluator infrastructure errors from candidate test failures (supporting clean re-runs on sealed artifacts).
- [ ] **Reviewer Interface & Reporting (`apps/web` + `apps/api`):**
  - [ ] Implement `GET /review/rubric`, `POST /review/ratings`, `POST /review/finalize`, `GET /sessions/{id}/report`, and `GET /reports` with reviewer/employer RBAC and `409 REVIEW_REVISION_CONFLICT` protection.
  - [ ] Build unified Reviewer Workspace displaying Stage A snapshot, Stage B snapshot & diff, visible/hidden test results, AI conversation log, synchronized transcript timeline (with click-to-jump and correction history), written reasoning, and Stage C defense responses.
  - [ ] Enforce separate Stage A (Independent) and Stage B (AI-Assisted) 1–5 anchored ratings + `Insufficient Evidence`, requiring cited `evidence_ids` for every numeric score and prohibiting naive Stage B − Stage A "AI uplift" calculations or automated hire/reject verdicts.
  - [ ] Build Employer Assessment Report view enforcing **SEC-010** (explicitly listing enforced `integrity_controls` and remote-assessment `limitations`, separating observed facts, deterministic test outcomes, and reviewer interpretations).
- [ ] **Pilot Hardening & Calibration:**
  - [ ] Wire OpenTelemetry tracing, structured JSON logs (redacting secrets/PII), and operational health/orphan-sandbox monitoring.
  - [ ] Execute full pre-pilot adversarial security test suite (`implementation_plan.md` §12: cross-tenant/cross-session authz, benign sandbox escape probes, egress blocks, secret leakage scan, ticket replay, transition races, revision conflicts, hidden-test isolation, audio deletion, crash cleanup).
  - [ ] Run supervised Assessment 001 calibration with ≥3 qualified senior backend engineers and ≥2 independent human reviewers (`assessment_001.md` §10).
- [ ] **M8 Exit Gate (MVP Complete):** Full end-to-end assessment lifecycle and pilot acceptance criteria verified with zero open P0/P1 security, isolation, or evidence-integrity defects.
