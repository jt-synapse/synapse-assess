# Trust domains and data flow

| Domain | Responsible for | Authorized data flow |
| --- | --- | --- |
| Browser | Local editor buffers, terminal presentation, assessment controls, consent and capture | Authenticated control-plane APIs carry candidate-visible files, revision-aware saves, terminal frames, authorized reasoning and AI messages. Server responses determine current permissions and deadlines. |
| Control plane | Identity and tenancy, session policy, provider adapters, leases, evidence ingestion, authorized review | Issues session-bound operations to execution providers. Writes platform PostgreSQL and artifact storage under service identities. Sends approved and disclosed context to AI or transcription providers only under the applicable stage and consent rules. |
| Candidate execution | Candidate workspace, processes, PTY and declared package services | Receives the candidate package, resource limits, an expiring lease, and any attempt-scoped database credentials. The broker retrieves source snapshots and observed execution results. Default-deny egress and filesystem confinement protect other domains. |
| Trusted evaluation | Fresh isolated runs of a sealed submission and a private grading package | Receives a read-only source artifact and package versions. A trusted harness owns result ingestion. The submitted process remains untrusted and must not read private grading materials, write the result channel, or acquire evaluator credentials. |

## Local development

The root Compose stack runs trusted application services and the platform database. The OrderFlow author-validation workflow runs the project-authored starter and references against a disposable test database. Live candidate code requires a selected and verified managed sandbox. The fixture provider exists only for protocol tests.

## Stage boundaries

1. Authorize each operation against current organization, session, and stage. Verify sandbox ownership at the broker.
2. Before a structured run, synchronize accepted edits, resolve terminal-side mutations, and bind the execution to the revision actually run. Preserve the broker's observable result.
3. When sealing, prevent new writes and execution, revoke ongoing terminal access, settle accepted operations, and verify the durable source artifact. Release the next stage only after its predecessor's seal is recorded.
4. Recover working files and application-consistent database state with the appropriate checkpoints. Formal snapshots at provisioning, Stage A, Stage B, and submission remain independently identifiable.
5. Separate candidate-visible results from evaluator and reviewer records. Sequence events at ingestion and record corrections and sensitive access under the approved policy.

## Architecture decision review

The accepted baseline covers [managed isolation](../decisions/ADR-001.md), [the browser IDE](../decisions/ADR-002.md), [disposable databases](../decisions/ADR-003.md), [the AI gateway](../decisions/ADR-004.md), and [conditional in-sandbox PostgreSQL](../decisions/ADR-011.md).

The following records are ready for formal review. Record the reviewer's disposition, date, and any conditions in each record on ratification.

- [Modular FastAPI control plane](../decisions/ADR-005.md)
- [Append-only evidence](../decisions/ADR-006.md)
- [Server-authoritative lifecycle](../decisions/ADR-007.md)
- [Consented transcription](../decisions/ADR-008.md)
- [Separate trusted grading](../decisions/ADR-009.md)
- [Immutable assessment versions](../decisions/ADR-010.md)
