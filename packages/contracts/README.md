# Shared contracts

The Python models are the source for the assessment manifest, REST payloads, streaming frames, and evidence envelope. Run `uv run python -m synapse_contracts.generate` from a workspace checkout after editing models or the route catalog. Run the same command with `--check` to detect stale exports. The TypeScript workspace exports the declarations as `@synapse/contracts`. The TypeScript consumer check and pytest load values derived from the same JSON fixtures.

## Implementation status

The generated OpenAPI 3.1 document lists REST operations under `paths`, with `x-availability` and `x-caller` on every operation. M0 serves the two health checks. Session, candidate and reviewer operations are planned contracts. The `x-websockets` extension describes the terminal and audio channels with separate client and server frames. The running API serves its own OpenAPI inventory for routes actually registered.

## Using the contracts

- Validate a manifest with `AssessmentManifest.model_validate_json(...)`. For publication and provisioning, call `require_published()` after a trusted build has resolved and verified its image and artifact digests. Source manifests may contain null digests. The candidate bundle and evaluator bundle occupy disjoint paths. Only the former is provisioned into a candidate sandbox. A manifest with `services: []` provisions no database.
- The server resolves the organization, actor, session, stage, deadline and tool permissions from authenticated state. The candidate can request completion of the current stage by presenting its `stage_attempt_id` and synchronized revision. Only the server determines the transition after sealing.
- File changes carry an operation ID and expected revision. Reusing an operation ID retries the original request. A mismatched revision produces `409 WORKSPACE_REVISION_CONFLICT`. File creation compares the workspace revision. Rename requires an unoccupied destination. Execution references an approved command ID and a synchronized workspace revision. Broker implementations must bind the run to that revision and confine resolved paths in the sandbox, including symlinks.
- Terminal tickets expire, may be redeemed once, and are bound to a session and sandbox. Terminal and audio brokers must check origin and current session authorization. Audio streaming additionally requires current, unrevoked consent. Deduplicate chunks by stream ID and sequence and persist finalized transcript segments as evidence. Append corrections as separate events.
- HTTP resource creation marked with `Idempotency-Key` must scope the key to the actor, operation and session. Retry responses must correspond to the original input. The evidence store assigns the per-session `server_sequence` and `received_at`. A manifest's string `stage_id` identifies its stage definition, while `stage_attempt_id` identifies the occurrence. Both are null on events preceding a stage. Pagination cursors are opaque. Apply authorization and visibility filters before paginating or resolving artifact references.
- Keep reviewer-only materials behind reviewer access controls. A numeric rating requires evidence IDs. A null score with an explanation records insufficient evidence. An amended rating is a new auditable revision. Finalization checks the expected revision.

The generated TypeScript declarations describe wire shapes. Runtime validation, authorization, artifact digest verification and filesystem confinement occur at their trusted boundaries.
