We have a solid architecture baseline for Synapse Assess. Before implementation, I want to resolve the remaining decisions systematically, focusing on cost, security, developer experience, operational complexity, and future scalability.

I would separate them into three categories.

## Remaining architecture decisions

| Priority | Decision                       | What we need to establish                                      |
| -------- | ------------------------------ | -------------------------------------------------------------- |
| P0       | Sandbox provider               | Where candidate code executes and how it is isolated           |
| P0       | PostgreSQL provisioning        | How each candidate gets a disposable database                  |
| P0       | Workspace persistence          | How code survives disconnections and stage transitions         |
| P0       | AI provider and model          | What powers the assisted stage                                 |
| P0       | Assessment integrity           | What controls are enforced and what we can legitimately verify |
| P1       | Speech-to-text provider        | How spoken reasoning becomes timestamped evidence              |
| P1       | Evidence storage and retention | What we capture, preserve, and delete                          |
| P1       | Authentication                 | How candidates, employers, and reviewers access the system     |
| P1       | Hosting and deployment         | Where the application and supporting services run              |
| P1       | Observability and recovery     | How we detect and recover from failures                        |

P0 decisions should be resolved before the first end-to-end implementation. P1 decisions can initially use replaceable defaults, but must be finalized before external pilots.

## Decision 1: Managed sandbox infrastructure

This is where I would start because it affects almost every other component.

We need a provider capable of running a realistic Python/FastAPI repository, supporting interactive terminal sessions, executing tests, and connecting to an isolated PostgreSQL instance.

Three providers are worth evaluating:

[E2B Trust Center](https://images.openai.com/static-rsc-4/cF-BSFZ1ExllAlFWUyppYl5iMM6rAGPhNvtVffMnEco8nIq1JWd6EDIN1HJ4cdJYqSi_vWzOgnHYOD0IDZFju8u115Y9v4GCaxdVqZiKimMYcFaIiCon-ACDHlgksjXYUoQH8eh54-vjIwz62ZOY-L22qcYQjWTBI9-04cNcquY?purpose=inline)

E2B

Developer-oriented cloud sandboxes with filesystem and command execution capabilities.

A strong initial candidate for the browser IDE and AI-assisted workflow. Verify terminal streaming, PostgreSQL deployment, and lifecycle pricing.

[E2B](https://e2b.dev?utm_source=chatgpt.com)

[Daytona: $24 Million Series A Raised For Building Composable Computers For AI Agents](https://images.openai.com/static-rsc-4/5y6ZAznV0vK7iuPM2qf0PL0AtYOkvVGjEdsTRqb1HPU9qb-fuShmjDXyqQAH-oPZ_oGxE4A-xKG9VTg9PEvkEGZGohQsVZ0tfLBvB6ql1so1hZUY6nF3T21Mb31BSfVrdY_H2ozzM8lji6ndzdXDQeIwtxU-RqrdukVUhc4VASk?purpose=inline)

Daytona

Programmable development environments and sandbox infrastructure.

Worth testing for persistent workspaces, development tooling, and snapshot behavior.

[Daytona](https://www.daytona.io?utm_source=chatgpt.com)

[クラウドベースのインフラストラクチャを提供するModal LabsがシリーズAで1,600万ドルの資金調達を実施｜STARTUP LOG｜スタートアップの挑戦を、もっと身近に｜スタログ｜STALOG｜](https://images.openai.com/static-rsc-4/g77qzWfQaNdnzyd-gKVIZndIHHoeBiZCtncnMO8-t0_QqMhfESX7sPPTUcAcGzWf07t9NaIfRycaZ2Z3dNABN6OHFHN8x4e12CUsojnBcLkhPXgdqB6l9mQ_oqNYzWbri0F_OAOFVt-El6U_xoAa5LIDAL09WiMg7OmVOylMo7M?purpose=inline)

Modal

Programmable cloud compute and isolated execution capabilities.

Potentially attractive for evaluation workers and short-lived execution workloads, though the interactive IDE requirements need testing.

[Modal](https://modal.com?utm_source=chatgpt.com)

These are candidates for benchmarking, not a verified ranking of their current capabilities or pricing.

### My initial recommendation

Start by evaluating E2B and Daytona. Use Modal as a third candidate if the first two do not satisfy the requirements.

I would test five capabilities before selecting one:

1. Provision a sandbox from a pinned image.
2. Run FastAPI and PostgreSQL with appropriate isolation.
3. Attach an interactive terminal.
4. Save and restore a workspace snapshot.
5. Destroy all resources reliably and measure total cost.

The provider should be replaceable, but that does not mean we should spend weeks building a universal abstraction. Support one implementation initially behind a small, stable interface.

## Decision 2: PostgreSQL isolation

Your requirement for a dedicated database per assessment attempt is sensible, particularly because Assessment 001 evaluates transactional consistency and concurrency.

There are two practical implementations.

Option A — PostgreSQL inside the candidate's isolated sandbox

The application and database run within the same isolated environment. This simplifies networking and cleanup but consumes additional resources and may require a custom sandbox image.

Option B — Separate disposable PostgreSQL instance

The candidate sandbox connects to a separately provisioned database. This provides a clearer database isolation boundary but adds provisioning latency, cost, networking, and cleanup complexity.

For the first prototype, I prefer Option A, provided the managed sandbox supports it securely and reliably. It still satisfies the dedicated disposable database requirement.

For commercial deployment, we can reconsider Option B based on isolation testing and provider capabilities.

## Decision 3: Workspace persistence

I recommend three distinct storage mechanisms.

| Storage                   | Purpose                                            | Lifetime                              |
| ------------------------- | -------------------------------------------------- | ------------------------------------- |
| Active sandbox filesystem | Candidate's working repository                     | Active assessment                     |
| Recovery checkpoints      | Restore after infrastructure failure               | Assessment plus short recovery window |
| Immutable stage snapshots | Preserve Stage A, Stage B, and submission evidence | Defined assessment retention period   |

This avoids relying on one mechanism for editing, recovery, and audit evidence.

The important architectural choice is that the active sandbox is disposable, but submitted work is not.

## Decision 4: AI provider

I would retain the provider-neutral gateway but start with one hosted model.

Do not attempt to support every model provider initially.

The first provider must support reliable tool interactions, reasonable latency, and predictable usage costs. We also need to version the model configuration so assessment sessions can be compared meaningfully.

A local LLM may be useful for development, but I would not make local inference a requirement for the first commercial pilot.

## Decision 5: Assessment integrity

I recommend treating integrity as a set of explicit controls rather than a single security score.

For Assessment 001:

- Stage A disables the platform's AI assistant.
- Candidate sandbox network egress is restricted.
- Stage transitions are server-enforced.
- Code snapshots and execution results are preserved.
- Stage B AI interactions are logged.
- Candidate identity and consent are recorded.
- Reviewers see material integrity exceptions.

The system must not claim that a remote candidate was definitively AI-free.

## My recommended way to proceed

We should make these decisions one at a time and record the rationale, alternatives, consequences, and acceptance criteria.

Let's start with PostgreSQL provisioning, because it gives us a concrete requirement against which to evaluate sandbox providers.

Where should each assessment's PostgreSQL database run?

Inside the isolated candidate sandbox (recommended)

Simpler provisioning, lower infrastructure complexity, and coordinated cleanup.

In a separate disposable database environment

Stronger separation between code execution and database infrastructure, but more operational complexity.

Confirm and continue&#x20;

Once this is settled, we can evaluate sandbox providers against a concrete architecture rather than choosing a vendor first and adapting the product to its limitations.

# Synapse Assess — Managed Sandbox Provider Benchmark

Benchmark Specification SB-001 · E2B vs. Daytona · November 2026

## 1. Executive recommendation

I recommend a controlled, reproducible benchmark comparing E2B and Daytona using identical workloads, resource budgets, and acceptance criteria.

Do not select a provider based on its SDK documentation or advertised startup latency alone.

Synapse Assess needs an interactive development environment that can remain available throughout a technical assessment, run background processes and databases, stream terminal I/O, preserve candidate work, and safely execute untrusted code.

The benchmark should determine whether either provider can support those requirements without substantial custom infrastructure.

## Benchmark objectives

Providers

# 2

E2B and Daytona

Test categories

# 7

Lifecycle, database, terminal, files, recovery, security, economics

Reference workload

### Python + PostgreSQL

Assessment 001 configuration

Selection rule

### Security first

Mandatory gates before weighted scoring

The benchmark will use Assessment 001 as the first representative workload, but the provider must not be selected solely because it handles Python and PostgreSQL.

We should also test a lightweight, database-free environment to verify that Synapse Assess can provision different assessment types without unnecessary infrastructure.

## 2. What we are actually comparing

The provider must support three distinct workloads.

| Workload         | Description                                             | Why it matters                 |
| ---------------- | ------------------------------------------------------- | ------------------------------ |
| W1 — Minimal     | Python runtime, filesystem, shell, no database          | Baseline provisioning and cost |
| W2 — Backend     | Python/FastAPI, PostgreSQL, tests, long-lived processes | Assessment 001                 |
| W3 — Interactive | File editing, terminal streaming, reconnects, snapshots | Candidate IDE experience       |

The benchmark should also measure a trusted grading execution separately, because grading has different security and lifecycle requirements from an interactive candidate workspace.

### Benchmark principles

- Run equivalent workloads with matched CPU, memory, and storage allocations where possible.
- Use pinned runtime images and dependency versions.
- Record cold starts separately from warm starts.
- Measure end-to-end latency, not only SDK response time.
- Repeat performance tests enough to estimate variability.
- Treat missing capabilities as implementation costs rather than assuming they exist.
- Validate isolation and security claims using documentation and controlled tests.
- Compare total cost per completed assessment, not merely advertised compute rates.

## 3. Initial provider findings

Current documentation indicates that both providers deserve evaluation, but their architectural models differ.

| Capability                      | E2B                          | Daytona                            |
| ------------------------------- | ---------------------------- | ---------------------------------- |
| Isolated execution              | Linux microVM model          | Container and VM classes           |
| Custom environments             | Templates                    | Images and snapshots               |
| Shell/process execution         | Documented                   | Documented                         |
| Interactive terminal            | PTY support advertised       | Terminal sessions documented       |
| Snapshot capabilities           | Pause, snapshot, restore     | Filesystem and VM memory snapshots |
| Persistent processes            | Supported in running sandbox | Process execution supported        |
| PostgreSQL inside sandbox       | Must benchmark               | Must benchmark                     |
| Network policy                  | Egress controls advertised   | Must verify selected sandbox class |
| 90-minute uninterrupted session | Plan-dependent               | Plan-dependent; verify             |
| Total session cost              | Must measure                 | Must measure                       |

E2B describes a microVM-based architecture with PTY access, network controls, and snapshot lifecycle operations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://e2b.dev\&sz=32)

The Enterprise AI Agent Cloud+1



Daytona documents process execution, filesystem and Git operations, terminal sessions, and multiple sandbox classes. Its snapshot behavior differs between container and VM environments.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.daytona.com\&sz=32)

Daytona+2



Two findings materially affect our design.

First, E2B plan limits need attention. Available billing documentation describes a one-hour continuous runtime limit on its lower tier and longer runtimes on Pro. Assessment 001 is 90 minutes, excluding provisioning and review preparation. We must verify the current applicable limits before assuming one uninterrupted session will work.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Second, snapshot support is not equivalent to application-consistent PostgreSQL recovery. Both providers expose snapshot functionality, but the benchmark must establish what happens to database transactions, write-ahead logs, active connections, and application processes during capture and restoration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Neither provider should be declared the winner from documentation alone.

## 4. Benchmark environment

I recommend two resource configurations.

| Resource                     | Standard      | Stress         |
| ---------------------------- | ------------- | -------------- |
| vCPU                         | 2             | 4              |
| RAM                          | 4 GiB         | 8 GiB          |
| Storage                      | 8 GiB minimum | 16 GiB minimum |
| Python                       | 3.12          | 3.12           |
| PostgreSQL                   | 16            | 16             |
| Assessment duration          | 90 min        | 90 min         |
| Concurrent terminal sessions | 1             | 2              |
| Simultaneous test processes  | 1             | 4              |

These are target configurations. If a provider does not offer an exact size, use the closest supported configuration and normalize cost and performance comparisons accordingly.

The sandbox image should include Python, PostgreSQL, Git, pytest, required dependencies, and the assessment's candidate-visible starter repository.

Hidden tests and reference solutions must not be included in the candidate image.

### Required benchmark instrumentation

Record server-side monotonic timing, API errors, resource usage, provider charges, and cleanup status.

Each test run should capture a unique run ID, provider, region, sandbox class, image digest, SDK version, and test configuration.

This makes comparisons reproducible and prevents misleading conclusions from inconsistent environments.

## 5. Benchmark test suite

### Test group A — Provisioning and lifecycle

Measure the time from requesting a sandbox to the point where Python, the filesystem, terminal, and PostgreSQL are ready.

| Test                   | Measurement                  | Proposed acceptance                     |
| ---------------------- | ---------------------------- | --------------------------------------- |
| Cold provisioning      | Request to ready             | P95 ≤ 30 seconds                        |
| Warm provisioning      | Request to ready             | P95 ≤ 10 seconds                        |
| Health check           | Ready state accuracy         | No false-ready results                  |
| Session longevity      | Continuous operation         | At least 110 minutes                    |
| Termination            | Request to resource deletion | P95 ≤ 30 seconds                        |
| Cleanup reconciliation | Orphan detection             | All test resources eventually reclaimed |

Run 30 cold starts and 30 warm starts per provider and configuration. Record median, P95, maximum, and failure rate.

The 110-minute requirement allows for the 90-minute assessment plus onboarding and operational overhead.

These thresholds are initial product targets, not verified provider performance.

### Test group B — In-sandbox PostgreSQL

This is a mandatory gate.

Each sandbox must independently initialize and operate PostgreSQL without relying on a shared production database.

Required test sequence

1. Initialize PostgreSQL with attempt-scoped credentials.
2. Apply migrations and load seed data.
3. Start FastAPI and execute basic database queries.
4. Run competing inventory reservation transactions.
5. Restart the application without restarting PostgreSQL.
6. Restart PostgreSQL and verify recovery.
7. Capture a consistent checkpoint and restore it.
8. Destroy the sandbox and verify database removal.

| Test                    | Pass condition                            |
| ----------------------- | ----------------------------------------- |
| Database startup        | Healthy and reachable locally             |
| Transaction rollback    | No partial committed reservation          |
| Concurrency             | Inventory invariant preserved             |
| Application restart     | Database remains available                |
| Database restart        | Committed data survives                   |
| Candidate DB privileges | No platform or cross-sandbox access       |
| Recovery checkpoint     | Data and schema restored consistently     |
| Resource containment    | Database failure affects only its sandbox |

The database should run as a supervised service rather than relying on an interactive terminal session to keep it alive.

Special test: Deliberately interrupt PostgreSQL during an active transaction, restore the sandbox, and verify recovery and transaction consistency.

A filesystem snapshot taken during active writes should not automatically be considered a valid database backup.

### Test group C — Interactive terminal streaming

A technical interview is interactive. A terminal that responds slowly or loses output creates candidate frustration and compromises assessment fairness.

Test:

- Shell creation and initial prompt latency.
- Keystroke echo and command responsiveness.
- Long-running command output.
- Terminal resizing.
- Ctrl+C and process termination.
- Browser disconnect and reconnection.
- Simultaneous file edits and terminal execution.
- Terminal revocation when an assessment stage closes.

| Metric               | Initial target                    |
| -------------------- | --------------------------------- |
| Terminal connection  | P95 ≤ 2 seconds                   |
| Keystroke echo       | P95 ≤ 150 ms                      |
| Output loss          | Zero for controlled test payloads |
| Reconnect            | P95 ≤ 5 seconds                   |
| Stage-end revocation | ≤ 2 seconds                       |
| Cross-session access | Zero successful attempts          |

For terminal latency, test from the intended candidate region as well as from the backend. Provider API latency alone does not represent the end-user experience.

### Test group D — Filesystem and workspace consistency

This tests the interaction between Monaco and the sandbox.

Critical test: Save → Execute → Verify

Edit

Save

Execute

Verify

The benchmark must verify that the executed code matches the recorded workspace revision.

Additional tests include large-file editing, concurrent save conflicts, rename operations, binary-file restrictions, symlink traversal, and reconnection with unsaved changes.

A successful provider must support a reliable file synchronization strategy, even if Synapse Assess implements revision tracking itself.

### Test group E — Snapshots and recovery

We need to distinguish three different capabilities.

| Capability                     | Purpose                       |
| ------------------------------ | ----------------------------- |
| Workspace checkpoint           | Restore candidate files       |
| Database-consistent checkpoint | Restore PostgreSQL safely     |
| Immutable stage artifact       | Preserve evidence for grading |

These should not be conflated.

For both providers, measure snapshot creation time, restoration time, storage cost, and consistency.

Test snapshots during idle periods, active file edits, database writes, and application execution.

For Stage A sealing, the system should stop new candidate mutations, synchronize files, establish a database-consistent checkpoint where recovery requires it, and preserve an immutable source snapshot.

A provider does not need native memory snapshots to pass if a reliable application-level recovery mechanism meets the requirements.

### Test group F — Security and isolation

Security is a mandatory pass/fail gate, not a feature that can be offset by low pricing.

| Test                             | Required outcome |
| -------------------------------- | ---------------- |
| Cross-sandbox filesystem access  | Denied           |
| Cross-sandbox network access     | Denied           |
| Platform credential access       | Denied           |
| Unauthorized outbound traffic    | Denied           |
| Candidate access to hidden tests | Denied           |
| Privileged host operations       | Denied           |
| CPU/memory exhaustion            | Contained        |
| Process exhaustion               | Contained        |
| Sandbox expiration               | Access revoked   |
| Terminal ticket replay           | Rejected         |

Test network restrictions at both the provider and application layer.

Do not assume a sandbox is safe merely because the vendor describes it as isolated. Review the provider's isolation model, security documentation, incident response commitments, and available independent assessments.

Use controlled, authorized security tests rather than attempting disruptive attacks against shared infrastructure.

### Test group G — Concurrency and reliability

Simulate increasing numbers of simultaneous candidates.

Load-test progression

## 1

sessions

## 5

sessions

## 10

sessions

## 25

sessions

Increase concurrency only after the preceding level passes. Confirm provider quotas and billing limits first.

At each level, measure provisioning success, terminal latency, test execution time, memory pressure, database availability, and cleanup reliability.

For the first commercial pilot, ten simultaneous assessments would be a reasonable initial capacity target. Twenty-five is a useful stress target rather than a launch requirement.

## 6. Cost benchmarking

We should compare the fully loaded infrastructure cost per completed assessment, not just the cost of a running sandbox.

Include provisioning, active runtime, storage, snapshots, recovery, networking, and any provider subscription allocation.

AI inference, transcription, and human review should be tracked separately because they do not necessarily depend on sandbox selection.

### Interactive cost model

Provider cost scenario

&#x20;Reset

Billable runtime110 min

Compute rate (hypothetical)$0.25/hr

Storage/network/checkpoint allowance$0.20

Additional fee per assessment$0.00

Monthly provider base fees$100

Completed assessments per month100

Cost per completed assessment

# $1.66

Monthly provider spend

# $165.83

Illustrative calculator, not E2B or Daytona pricing. Assumes all attempts complete successfully and excludes AI, STT, grading, taxes, and application hosting.

For the benchmark, use actual provider invoices or metered usage and calculate:

\\[ C\_{\text{assessment}} = C\_{\text{compute}}+ C\_{\text{storage}}+ C\_{\text{network}}+ C\_{\text{snapshots}}+ C\_{\text{fees}} \\]

Report failed attempts and abandoned sandboxes separately. They still generate cost.

I would use a provisional target of $5 or less in sandbox infrastructure cost per completed 90-minute assessment, with a stretch target of $3. These are internal economic goals, not known provider rates.

## 7. Provider scorecard

Security, database correctness, and lifecycle reliability are mandatory gates. Only providers passing those gates receive a weighted score.

Benchmark scoring worksheet

Enter measured scores from 0 (fails) to 5 (excellent). Blank entries are untested and count as zero. Scores do not establish mandatory-gate compliance.

| Criterion                                  | E2B | Daytona |
| ------------------------------------------ | --- | ------- |
| Security and isolation<br>25% weight       | —   | —       |
| PostgreSQL correctness<br>20% weight       | —   | —       |
| Terminal and IDE experience<br>15% weight  | —   | —       |
| Lifecycle and recovery<br>15% weight       | —   | —       |
| Cost<br>15% weight                         | —   | —       |
| SDK and developer experience<br>10% weight | —   | —       |

E2B weighted score

# 0/100

Incomplete evaluation

Daytona weighted score

# 0/100

Incomplete evaluation

### Selection thresholds

I would require a provider to satisfy all mandatory security and correctness gates, achieve at least 80/100 overall, and score at least 3/5 in every category.

If both pass, prefer the provider with lower measured total cost and operational complexity, provided its candidate experience is comparable.

If neither passes, revisit the provider shortlist rather than weakening the isolation requirements.

## 8. Execution plan and deliverables

Day 1 — Common benchmark workload

Define pinned runtime image, PostgreSQL setup, test scripts, resource profiles, and measurement format.

Days 2–3 — Provider integration

Implement minimal E2B and Daytona adapters and run provisioning, database, terminal, and filesystem tests.

Days 4–5 — Recovery and security

Test snapshots, reconnects, network restrictions, resource exhaustion, and cleanup.

Days 6–7 — Performance and cost

Repeat lifecycle measurements, run controlled concurrency tests, collect actual usage charges, and complete the scorecard.

### Final benchmark artifacts

The benchmark should produce a provider comparison report, raw measurement results, test logs, security findings, cost model, and a formal provider-selection ADR.

The selected provider should then be implemented behind the Synapse Assess sandbox adapter. The rejected provider's benchmark results should be retained for future reassessment.

## 9. Go/no-go criteria

## Provider selection gate

All critical conditions must be satisfied before adopting a provider for external candidate assessments.

Dedicated PostgreSQL starts and operates reliably

90-minute assessment plus operational buffer supported

Interactive terminal meets latency and reconnect targets

Candidate code cannot access other attempts or platform secrets

Workspace and database recovery are consistent

Hidden-test execution remains isolated

Sandbox cleanup and expiration are reliable

Measured costs fit the target unit economics

0 of 8 verified

Evaluation pending

This is a planning checklist; selecting boxes does not independently verify provider compliance.

## Final recommendation

Proceed with an E2B-versus-Daytona benchmark. Do not commit to either provider yet.

The primary decision is whether either provider can support a 90-minute interactive assessment with in-sandbox PostgreSQL, reliable snapshots, secure isolation, and acceptable per-session cost.

I would test E2B first because its documented microVM, PTY, and lifecycle capabilities align closely with the proposed execution architecture. Daytona should receive the same tests rather than being treated as a fallback.

Architecture status: Benchmark specification complete; provider selection remains open. No benchmark has been executed, no performance results have been measured, and no files have been created.

Once this decision is resolved, the next architecture topic should be workspace persistence and recovery, particularly how we guarantee that candidates never lose submitted code or reasoning evidence when a sandbox fails.

# Synapse Assess — Managed Sandbox Provider Benchmark

Benchmark Specification SB-001 · E2B vs. Daytona · November 2026

## 1. Executive recommendation

I recommend a controlled, reproducible benchmark comparing E2B and Daytona using identical workloads, resource budgets, and acceptance criteria.

Do not select a provider based on its SDK documentation or advertised startup latency alone.

Synapse Assess needs an interactive development environment that can remain available throughout a technical assessment, run background processes and databases, stream terminal I/O, preserve candidate work, and safely execute untrusted code.

The benchmark should determine whether either provider can support those requirements without substantial custom infrastructure.

## Benchmark objectives

Providers

# 2

E2B and Daytona

Test categories

# 7

Lifecycle, database, terminal, files, recovery, security, economics

Reference workload

### Python + PostgreSQL

Assessment 001 configuration

Selection rule

### Security first

Mandatory gates before weighted scoring

The benchmark will use Assessment 001 as the first representative workload, but the provider must not be selected solely because it handles Python and PostgreSQL.

We should also test a lightweight, database-free environment to verify that Synapse Assess can provision different assessment types without unnecessary infrastructure.

## 2. What we are actually comparing

The provider must support three distinct workloads.

| Workload         | Description                                             | Why it matters                 |
| ---------------- | ------------------------------------------------------- | ------------------------------ |
| W1 — Minimal     | Python runtime, filesystem, shell, no database          | Baseline provisioning and cost |
| W2 — Backend     | Python/FastAPI, PostgreSQL, tests, long-lived processes | Assessment 001                 |
| W3 — Interactive | File editing, terminal streaming, reconnects, snapshots | Candidate IDE experience       |

The benchmark should also measure a trusted grading execution separately, because grading has different security and lifecycle requirements from an interactive candidate workspace.

### Benchmark principles

- Run equivalent workloads with matched CPU, memory, and storage allocations where possible.
- Use pinned runtime images and dependency versions.
- Record cold starts separately from warm starts.
- Measure end-to-end latency, not only SDK response time.
- Repeat performance tests enough to estimate variability.
- Treat missing capabilities as implementation costs rather than assuming they exist.
- Validate isolation and security claims using documentation and controlled tests.
- Compare total cost per completed assessment, not merely advertised compute rates.

## 3. Initial provider findings

Current documentation indicates that both providers deserve evaluation, but their architectural models differ.

| Capability                      | E2B                          | Daytona                            |
| ------------------------------- | ---------------------------- | ---------------------------------- |
| Isolated execution              | Linux microVM model          | Container and VM classes           |
| Custom environments             | Templates                    | Images and snapshots               |
| Shell/process execution         | Documented                   | Documented                         |
| Interactive terminal            | PTY support advertised       | Terminal sessions documented       |
| Snapshot capabilities           | Pause, snapshot, restore     | Filesystem and VM memory snapshots |
| Persistent processes            | Supported in running sandbox | Process execution supported        |
| PostgreSQL inside sandbox       | Must benchmark               | Must benchmark                     |
| Network policy                  | Egress controls advertised   | Must verify selected sandbox class |
| 90-minute uninterrupted session | Plan-dependent               | Plan-dependent; verify             |
| Total session cost              | Must measure                 | Must measure                       |

E2B describes a microVM-based architecture with PTY access, network controls, and snapshot lifecycle operations.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://e2b.dev\&sz=32)

The Enterprise AI Agent Cloud+1



Daytona documents process execution, filesystem and Git operations, terminal sessions, and multiple sandbox classes. Its snapshot behavior differs between container and VM environments.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://www.daytona.com\&sz=32)

Daytona+2



Two findings materially affect our design.

First, E2B plan limits need attention. Available billing documentation describes a one-hour continuous runtime limit on its lower tier and longer runtimes on Pro. Assessment 001 is 90 minutes, excluding provisioning and review preparation. We must verify the current applicable limits before assuming one uninterrupted session will work.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Second, snapshot support is not equivalent to application-consistent PostgreSQL recovery. Both providers expose snapshot functionality, but the benchmark must establish what happens to database transactions, write-ahead logs, active connections, and application processes during capture and restoration.&#x20;

[image](https://www.google.com/s2/favicons?domain=https://github.com\&sz=32)

GitHub+1



Neither provider should be declared the winner from documentation alone.

## 4. Benchmark environment

I recommend two resource configurations.

| Resource                     | Standard      | Stress         |
| ---------------------------- | ------------- | -------------- |
| vCPU                         | 2             | 4              |
| RAM                          | 4 GiB         | 8 GiB          |
| Storage                      | 8 GiB minimum | 16 GiB minimum |
| Python                       | 3.12          | 3.12           |
| PostgreSQL                   | 16            | 16             |
| Assessment duration          | 90 min        | 90 min         |
| Concurrent terminal sessions | 1             | 2              |
| Simultaneous test processes  | 1             | 4              |

These are target configurations. If a provider does not offer an exact size, use the closest supported configuration and normalize cost and performance comparisons accordingly.

The sandbox image should include Python, PostgreSQL, Git, pytest, required dependencies, and the assessment's candidate-visible starter repository.

Hidden tests and reference solutions must not be included in the candidate image.

### Required benchmark instrumentation

Record server-side monotonic timing, API errors, resource usage, provider charges, and cleanup status.

Each test run should capture a unique run ID, provider, region, sandbox class, image digest, SDK version, and test configuration.

This makes comparisons reproducible and prevents misleading conclusions from inconsistent environments.

## 5. Benchmark test suite

### Test group A — Provisioning and lifecycle

Measure the time from requesting a sandbox to the point where Python, the filesystem, terminal, and PostgreSQL are ready.

| Test                   | Measurement                  | Proposed acceptance                     |
| ---------------------- | ---------------------------- | --------------------------------------- |
| Cold provisioning      | Request to ready             | P95 ≤ 30 seconds                        |
| Warm provisioning      | Request to ready             | P95 ≤ 10 seconds                        |
| Health check           | Ready state accuracy         | No false-ready results                  |
| Session longevity      | Continuous operation         | At least 110 minutes                    |
| Termination            | Request to resource deletion | P95 ≤ 30 seconds                        |
| Cleanup reconciliation | Orphan detection             | All test resources eventually reclaimed |

Run 30 cold starts and 30 warm starts per provider and configuration. Record median, P95, maximum, and failure rate.

The 110-minute requirement allows for the 90-minute assessment plus onboarding and operational overhead.

These thresholds are initial product targets, not verified provider performance.

### Test group B — In-sandbox PostgreSQL

This is a mandatory gate.

Each sandbox must independently initialize and operate PostgreSQL without relying on a shared production database.

Required test sequence

1. Initialize PostgreSQL with attempt-scoped credentials.
2. Apply migrations and load seed data.
3. Start FastAPI and execute basic database queries.
4. Run competing inventory reservation transactions.
5. Restart the application without restarting PostgreSQL.
6. Restart PostgreSQL and verify recovery.
7. Capture a consistent checkpoint and restore it.
8. Destroy the sandbox and verify database removal.

| Test                    | Pass condition                            |
| ----------------------- | ----------------------------------------- |
| Database startup        | Healthy and reachable locally             |
| Transaction rollback    | No partial committed reservation          |
| Concurrency             | Inventory invariant preserved             |
| Application restart     | Database remains available                |
| Database restart        | Committed data survives                   |
| Candidate DB privileges | No platform or cross-sandbox access       |
| Recovery checkpoint     | Data and schema restored consistently     |
| Resource containment    | Database failure affects only its sandbox |

The database should run as a supervised service rather than relying on an interactive terminal session to keep it alive.

Special test: Deliberately interrupt PostgreSQL during an active transaction, restore the sandbox, and verify recovery and transaction consistency.

A filesystem snapshot taken during active writes should not automatically be considered a valid database backup.

### Test group C — Interactive terminal streaming

A technical interview is interactive. A terminal that responds slowly or loses output creates candidate frustration and compromises assessment fairness.

Test:

- Shell creation and initial prompt latency.
- Keystroke echo and command responsiveness.
- Long-running command output.
- Terminal resizing.
- Ctrl+C and process termination.
- Browser disconnect and reconnection.
- Simultaneous file edits and terminal execution.
- Terminal revocation when an assessment stage closes.

| Metric               | Initial target                    |
| -------------------- | --------------------------------- |
| Terminal connection  | P95 ≤ 2 seconds                   |
| Keystroke echo       | P95 ≤ 150 ms                      |
| Output loss          | Zero for controlled test payloads |
| Reconnect            | P95 ≤ 5 seconds                   |
| Stage-end revocation | ≤ 2 seconds                       |
| Cross-session access | Zero successful attempts          |

For terminal latency, test from the intended candidate region as well as from the backend. Provider API latency alone does not represent the end-user experience.

### Test group D — Filesystem and workspace consistency

This tests the interaction between Monaco and the sandbox.

Critical test: Save → Execute → Verify

Edit

Save

Execute

Verify

The benchmark must verify that the executed code matches the recorded workspace revision.

Additional tests include large-file editing, concurrent save conflicts, rename operations, binary-file restrictions, symlink traversal, and reconnection with unsaved changes.

A successful provider must support a reliable file synchronization strategy, even if Synapse Assess implements revision tracking itself.

### Test group E — Snapshots and recovery

We need to distinguish three different capabilities.

| Capability                     | Purpose                       |
| ------------------------------ | ----------------------------- |
| Workspace checkpoint           | Restore candidate files       |
| Database-consistent checkpoint | Restore PostgreSQL safely     |
| Immutable stage artifact       | Preserve evidence for grading |

These should not be conflated.

For both providers, measure snapshot creation time, restoration time, storage cost, and consistency.

Test snapshots during idle periods, active file edits, database writes, and application execution.

For Stage A sealing, the system should stop new candidate mutations, synchronize files, establish a database-consistent checkpoint where recovery requires it, and preserve an immutable source snapshot.

A provider does not need native memory snapshots to pass if a reliable application-level recovery mechanism meets the requirements.

### Test group F — Security and isolation

Security is a mandatory pass/fail gate, not a feature that can be offset by low pricing.

| Test                             | Required outcome |
| -------------------------------- | ---------------- |
| Cross-sandbox filesystem access  | Denied           |
| Cross-sandbox network access     | Denied           |
| Platform credential access       | Denied           |
| Unauthorized outbound traffic    | Denied           |
| Candidate access to hidden tests | Denied           |
| Privileged host operations       | Denied           |
| CPU/memory exhaustion            | Contained        |
| Process exhaustion               | Contained        |
| Sandbox expiration               | Access revoked   |
| Terminal ticket replay           | Rejected         |

Test network restrictions at both the provider and application layer.

Do not assume a sandbox is safe merely because the vendor describes it as isolated. Review the provider's isolation model, security documentation, incident response commitments, and available independent assessments.

Use controlled, authorized security tests rather than attempting disruptive attacks against shared infrastructure.

### Test group G — Concurrency and reliability

Simulate increasing numbers of simultaneous candidates.

Load-test progression

## 1

sessions

## 5

sessions

## 10

sessions

## 25

sessions

Increase concurrency only after the preceding level passes. Confirm provider quotas and billing limits first.

At each level, measure provisioning success, terminal latency, test execution time, memory pressure, database availability, and cleanup reliability.

For the first commercial pilot, ten simultaneous assessments would be a reasonable initial capacity target. Twenty-five is a useful stress target rather than a launch requirement.

## 6. Cost benchmarking

We should compare the fully loaded infrastructure cost per completed assessment, not just the cost of a running sandbox.

Include provisioning, active runtime, storage, snapshots, recovery, networking, and any provider subscription allocation.

AI inference, transcription, and human review should be tracked separately because they do not necessarily depend on sandbox selection.

### Interactive cost model

Provider cost scenario

&#x20;Reset

Billable runtime110 min

Compute rate (hypothetical)$0.25/hr

Storage/network/checkpoint allowance$0.20

Additional fee per assessment$0.00

Monthly provider base fees$100

Completed assessments per month100

Cost per completed assessment

# $1.66

Monthly provider spend

# $165.83

Illustrative calculator, not E2B or Daytona pricing. Assumes all attempts complete successfully and excludes AI, STT, grading, taxes, and application hosting.

For the benchmark, use actual provider invoices or metered usage and calculate:

\\[ C\_{\text{assessment}} = C\_{\text{compute}}+ C\_{\text{storage}}+ C\_{\text{network}}+ C\_{\text{snapshots}}+ C\_{\text{fees}} \\]

Report failed attempts and abandoned sandboxes separately. They still generate cost.

I would use a provisional target of $5 or less in sandbox infrastructure cost per completed 90-minute assessment, with a stretch target of $3. These are internal economic goals, not known provider rates.

## 7. Provider scorecard

Security, database correctness, and lifecycle reliability are mandatory gates. Only providers passing those gates receive a weighted score.

Benchmark scoring worksheet

Enter measured scores from 0 (fails) to 5 (excellent). Blank entries are untested and count as zero. Scores do not establish mandatory-gate compliance.

| Criterion                                  | E2B | Daytona |
| ------------------------------------------ | --- | ------- |
| Security and isolation<br>25% weight       | —   | —       |
| PostgreSQL correctness<br>20% weight       | —   | —       |
| Terminal and IDE experience<br>15% weight  | —   | —       |
| Lifecycle and recovery<br>15% weight       | —   | —       |
| Cost<br>15% weight                         | —   | —       |
| SDK and developer experience<br>10% weight | —   | —       |

E2B weighted score

# 0/100

Incomplete evaluation

Daytona weighted score

# 0/100

Incomplete evaluation

### Selection thresholds

I would require a provider to satisfy all mandatory security and correctness gates, achieve at least 80/100 overall, and score at least 3/5 in every category.

If both pass, prefer the provider with lower measured total cost and operational complexity, provided its candidate experience is comparable.

If neither passes, revisit the provider shortlist rather than weakening the isolation requirements.

## 8. Execution plan and deliverables

Day 1 — Common benchmark workload

Define pinned runtime image, PostgreSQL setup, test scripts, resource profiles, and measurement format.

Days 2–3 — Provider integration

Implement minimal E2B and Daytona adapters and run provisioning, database, terminal, and filesystem tests.

Days 4–5 — Recovery and security

Test snapshots, reconnects, network restrictions, resource exhaustion, and cleanup.

Days 6–7 — Performance and cost

Repeat lifecycle measurements, run controlled concurrency tests, collect actual usage charges, and complete the scorecard.

### Final benchmark artifacts

The benchmark should produce a provider comparison report, raw measurement results, test logs, security findings, cost model, and a formal provider-selection ADR.

The selected provider should then be implemented behind the Synapse Assess sandbox adapter. The rejected provider's benchmark results should be retained for future reassessment.

## 9. Go/no-go criteria

## Provider selection gate

All critical conditions must be satisfied before adopting a provider for external candidate assessments.

Dedicated PostgreSQL starts and operates reliably

90-minute assessment plus operational buffer supported

Interactive terminal meets latency and reconnect targets

Candidate code cannot access other attempts or platform secrets

Workspace and database recovery are consistent

Hidden-test execution remains isolated

Sandbox cleanup and expiration are reliable

Measured costs fit the target unit economics

0 of 8 verified

Evaluation pending

This is a planning checklist; selecting boxes does not independently verify provider compliance.

## Final recommendation

Proceed with an E2B-versus-Daytona benchmark. Do not commit to either provider yet.

The primary decision is whether either provider can support a 90-minute interactive assessment with in-sandbox PostgreSQL, reliable snapshots, secure isolation, and acceptable per-session cost.

I would test E2B first because its documented microVM, PTY, and lifecycle capabilities align closely with the proposed execution architecture. Daytona should receive the same tests rather than being treated as a fallback.

Architecture status: Benchmark specification complete; provider selection remains open. No benchmark has been executed, no performance results have been measured, and no files have been created.

Once this decision is resolved, the next architecture topic should be workspace persistence and recovery, particularly how we guarantee that candidates never lose submitted code or reasoning evidence when a sandbox fails.

Yes. Synapse Assess is ready to begin MVP development. I would not spend more time designing the entire architecture before starting implementation.

We have enough technical direction to build the first working version. Several decisions remain unresolved, but they can be addressed during development rather than blocking it.

The distinction is that we're ready to build an MVP, not ready to launch a production hiring platform.

## 1. Current readiness assessment

## MVP readiness

Ready to build

| Product vision and scope     |            |
| ---------------------------- | ---------- |
| Assessment 001 specification |            |
| System architecture          |            |
| API and data contracts       |            |
| Security boundaries          |            |
| Sandbox provider             | Pending    |
| Executable assessment        | Not built  |
| Infrastructure validation    | Not tested |

Completed items are specified at the design level, not implemented or independently verified.

We have defined the architecture sufficiently to avoid major ambiguity during initial development.

## 2. What I would build for MVP v0.1

The first milestone should demonstrate the complete core experience:

A candidate opens an assessment, writes code, runs tests, explains their reasoning aloud, uses AI during the permitted stage, and produces an evidence-backed report.

## MVP v0.1 — Functional scope

Implementation checklist

0/7 complete

Candidate assessment workspace

Monaco editor, file explorer, terminal and instructions

Managed sandbox execution

Isolated Python runtime with disposable PostgreSQL

Assessment stage orchestration

Independent stage, AI-assisted stage and submission

AI assistant

Provider-neutral gateway, enabled only in Stage B

Live reasoning capture

Microphone, transcription and timestamped evidence

Evidence timeline

Code changes, test runs, AI interactions and speech

Basic reviewer report

Human-readable assessment results and linked evidence

I would explicitly exclude billing, subscriptions, ATS integrations, physical interview pods, multiple assessment libraries, and automated hiring decisions.

## 3. Recommended build sequence

Milestone 0 — Project foundation

Establish the monorepo, Next.js frontend, FastAPI backend, PostgreSQL, Docker Compose, shared contracts, CI, and architecture documentation.

Exit criterion: Frontend and backend start locally, communicate successfully, and pass basic automated tests.

Milestone 1 — Working coding environment

Integrate Monaco, file operations, terminal, and a sandbox adapter.

Exit criterion: Open a repository, edit a file, run a test, and preserve the result.

Milestone 2 — Assessment engine

Implement stage transitions, timers, snapshots, and Assessment 001.

Exit criterion: Complete both coding stages with server-enforced AI permissions.

Milestone 3 — Reasoning and evidence

Add live transcription, event correlation, AI interaction logs, and a reviewer timeline.

Exit criterion: Reviewer can reconstruct the candidate's work and explanations.

Milestone 4 — Pilot hardening

Validate isolation, database consistency, recovery, accessibility, and candidate consent.

Exit criterion: A supervised pilot can run without unresolved critical security or reliability failures.

## 4. How I would approach the remaining decisions

Don't wait for every vendor decision before building the frontend, control plane, and assessment package.

Use interfaces and adapters to isolate external dependencies.

For the managed sandbox, I would conduct a short E2B-versus-Daytona spike during Milestone 1. Select a provider based on actual PostgreSQL, terminal, and lifecycle tests rather than choosing it theoretically.

For transcription, begin with one provider behind a replaceable interface. For AI, use one model behind the provider-neutral gateway.

These are implementation details that can evolve without changing the core product architecture.

## 5. One architectural adjustment before starting

I recommend maintaining a strict separation between:

- The platform: Assessment orchestration, candidate workspace, AI, transcription, evidence, and reporting.
- Assessment packages: Individual exercises, runtime requirements, tests, rubrics, and instructions.

Assessment 001 should be the first package installed into Synapse Assess, not hardcoded into the platform.

That distinction will allow future assessments involving TypeScript, React, distributed systems, and machine learning without rebuilding the application.

## My recommendation

Start building now, using Codex as the implementation agent and the finalized architecture as its technical contract.

I would begin with Milestone 0 and establish a working vertical slice as quickly as possible.

The first successful demonstration should be:

`Launch assessment → Provision sandbox → Open code in Monaco → Edit → Run test → Save evidence`

Once that works, extend the same workflow to the hybrid assessment stages, AI gateway, and microphone transcription.

You have enough architecture to start, and further theoretical planning is likely to produce diminishing returns.

The next concrete step is to create the Synapse Assess monorepo with its architecture documentation, development environment, and Milestone 0 implementation plan.