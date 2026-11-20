# Synapse Assess — Assessment 001

Senior Software Engineer · Backend Reliability & AI-Assisted Engineering · Specification v1.0

## OrderFlow: The Inventory Reservation Incident

Senior Level

A production-like order management service is experiencing intermittent inventory inconsistencies, duplicate reservations, and unreliable retries. The candidate must investigate the system, repair its critical behavior, extend it using an AI assistant, and defend their engineering decisions.

Duration

## 90 min

Language

## Python 3.12+

Framework

## FastAPI + PostgreSQL

Assessment format

## Hybrid

## 1. Assessment objectives

Assessment 001 evaluates whether a senior backend engineer can:

- Understand an unfamiliar production-style codebase.
- Diagnose concurrency and data-consistency defects.
- Implement reliable, maintainable fixes.
- Design idempotent API behavior.
- Use AI assistance critically rather than accepting generated code unconditionally.
- Explain technical decisions while working.
- Defend architecture choices under changing requirements.

The assessment is not a speed-coding competition. Candidates are evaluated on correctness, reasoning, verification, and engineering judgment.

## 2. Assessment structure

Stage A — Independent Debugging

35 minutes · AI assistance prohibited

Stage B — AI-Assisted Implementation

40 minutes · Controlled AI assistant enabled

Stage C — Technical Defense

15 minutes · Structured engineering discussion

## 3. Scenario and system architecture

### Candidate briefing

> You have joined the backend engineering team responsible for OrderFlow, an inventory reservation service used by an e-commerce platform.
>
> The service processes inventory reservations when customers submit orders. Recently, customers have been able to reserve more inventory than is available, and some retries have produced duplicate reservations.
>
> Your task is to investigate the existing implementation, restore correctness, and improve the system's reliability.
>
> You will first work independently. In the second stage, you will receive access to an AI engineering assistant and additional requirements.

### System architecture

The starter repository contains approximately 400–600 lines of application code, excluding dependencies and tests.

### Starter repository specification

```
assessment-001-orderflow/
├── README.md
├── pyproject.toml
├── docker-compose.yml
├── .env.example
├── app/
│   ├── main.py
│   ├── api/
│   │   └── reservations.py
│   ├── core/
│   │   ├── config.py
│   │   └── database.py
│   ├── models/
│   │   ├── inventory.py
│   │   └── reservation.py
│   ├── schemas/
│   │   └── reservation.py
│   ├── services/
│   │   └── reservation_service.py
│   └── repositories/
│       └── inventory_repository.py
├── tests/
│   ├── conftest.py
│   ├── test_reservations.py
│   ├── test_inventory.py
│   └── test_concurrency.py
└── docs/
    ├── architecture.md
    └── api_contract.md
```

The candidate receives a working development environment, sample requests, seeded data, and baseline tests. The service must be runnable before the assessment begins.

## 4. Stage A — Independent Engineering

35 MINUTES · NO GENERATIVE AI

### Candidate task

Investigate why OrderFlow sometimes permits more inventory to be reserved than is available.

Expected behavior:

- Inventory must never be over-reserved.
- Concurrent requests must preserve inventory invariants.
- Failed reservations must not leave partial changes.
- Existing successful reservation behavior must remain intact.

### Seeded defect A1: Non-atomic inventory update

The reservation service reads available inventory, checks whether sufficient quantity exists, and subsequently updates the record.

Two concurrent requests can read the same available quantity before either commits its update.

Expected senior-level insight: The candidate should recognize the time-of-check/time-of-use race and apply an appropriate database-level concurrency control strategy.

Acceptable approaches include a conditional atomic update or transactionally correct row locking.

### Seeded defect A2: Incorrect transaction boundary

The implementation creates a reservation record and updates inventory through separate commit operations.

If the second operation fails, the first may remain committed.

Expected insight: The candidate should identify the missing atomic transaction boundary and ensure both operations succeed or fail together.

### Required candidate deliverables

- A working correction to the reservation path.
- At least one regression test demonstrating the concurrency problem or verifying its prevention.
- A brief explanation of the root cause and chosen fix.
- No regression in the existing API contract.

### Stage A acceptance tests

| Test                                           | Expected result             |
| ---------------------------------------------- | --------------------------- |
| Reserve available inventory                    | Success                     |
| Reserve unavailable inventory                  | Rejected without mutation   |
| Two concurrent requests competing for one unit | Exactly one succeeds        |
| Database failure during reservation            | Entire operation rolls back |
| Existing API response behavior                 | Preserved                   |

The concurrent test must use separate database transactions against PostgreSQL. An in-memory SQLite test is not sufficient to validate PostgreSQL locking behavior.

## 5. Stage B — AI-Assisted Engineering

40 MINUTES · CONTROLLED AI ENABLED

### Candidate task

The product team has introduced a new requirement: clients must be able to retry reservation requests safely after network failures.

Implement idempotent reservation creation.

The endpoint accepts an `Idempotency-Key` header.

Required behavior:

- Repeating a successful request with the same key and equivalent payload returns the original reservation result.
- Concurrent requests with the same key must not create duplicate reservations.
- Reusing a key with a different payload returns a conflict.
- An invalid reservation must not become permanently cached as a successful operation.
- The idempotency mechanism must not break the Stage A inventory guarantees.

### AI assistant

The candidate receives access to a provided assistant with repository context and documented tool permissions.

The assistant can explain code, propose patches, and suggest tests. It cannot silently modify the repository or execute commands without the candidate's explicit approval.

The platform records AI requests, responses, accepted tool actions, and relevant code changes.

### Assessment design

The assistant should not be deliberately deceptive.

Instead, the evaluation should include realistic opportunities to verify AI output. For example, an assistant may suggest an application-level dictionary for storing idempotency keys.

That could work in a single-process demonstration but fail under multiple workers or restarts.

A strong candidate should recognize the limitation and select durable, concurrency-safe storage.

Do not score candidates negatively merely because the assistant produced an imperfect suggestion. Evaluate how they investigated and handled it.

### Stage B acceptance tests

| Test                                       | Expected result                       |
| ------------------------------------------ | ------------------------------------- |
| First request with a new key               | Creates one reservation               |
| Same key and same payload                  | Returns original result               |
| Same key with different payload            | Conflict                              |
| Concurrent same-key requests               | One reservation, consistent responses |
| Process restart followed by retry          | No duplicate reservation              |
| Failed transaction followed by retry       | Correctly recoverable                 |
| Different keys competing for limited stock | Inventory invariant preserved         |

For deterministic grading, the assessment must specify how idempotency keys are scoped, which request fields determine payload equivalence, how concurrent in-progress requests respond, and which response outcomes are persisted.

These are part of the assessment's API contract, not details to leave ambiguous.

## 6. Live reasoning capture

FEATURE RC-001 · ACTIVE DURING ALL THREE STAGES

The candidate is asked to explain their reasoning while working.

Microphone audio is transcribed into timestamped text and associated with code changes, test executions, and AI interactions.

### Candidate-facing prompts

The platform should use brief prompts at meaningful checkpoints rather than demanding continuous speech.

Reasoning checkpoints

1. Initial investigation

   "What part of the system are you investigating first, and why?"
2. Root-cause hypothesis

   "What do you believe is causing the defect, and what evidence supports that?"
3. Implementation decision

   "Explain the approach you've selected and any alternatives you considered."
4. AI-assisted stage

   "Which parts of the assistant's output did you accept, modify, or reject?"
5. Validation

   "How have you verified that your implementation behaves correctly?"

Prompts should be nonblocking and avoid interrupting critical debugging activity. Candidates may respond verbally or through an approved written alternative.

### Transcript and event correlation

Example synchronized evidence

- 12:42 · Transcript

  "Both requests can read the same stock value before the update."
- 13:08 · Code event

  Candidate edits `inventory_repository.py`.
- 15:21 · Test event

  Candidate executes `pytest tests/test_concurrency.py`.
- 15:24 · Result

  Concurrency regression test passes.

### Recording requirements

The implementation must support explicit consent, visible microphone status, timestamped transcript segments, secure transport, and recovery from temporary disconnections.

Raw audio should be retained only for a disclosed, limited period needed for quality checks or authorized review. The transcript and linked evidence should follow the employer's agreed retention policy.

Speech quantity, accent, pronunciation, and apparent confidence must not influence technical scoring. Transcription failures and approved written alternatives must not automatically disadvantage candidates.

## 7. Stage C — Technical Defense

15 MINUTES · HUMAN-REVIEWED

The candidate receives three structured questions based on their implementation.

### Question 1 — Concurrency

"Your solution works in the tests. What changes if the application runs across eight worker processes?"

Expected areas of discussion: database-enforced guarantees, process-local state, transactions, and concurrency across instances.

### Question 2 — Failure recovery

"What happens if the database commits the reservation but the API connection fails before the client receives the response?"

Expected areas: durable idempotency records, retry semantics, transaction boundaries, and response recovery.

### Question 3 — AI-assisted engineering

"Identify one AI-generated suggestion you accepted, modified, or rejected. Explain the evidence behind that decision."

Expected areas: independent validation, trade-offs, correctness, and technical ownership.

Reviewers may adapt follow-ups to the candidate's actual implementation, but must preserve equivalent competency coverage across candidates.

## 8. Evaluation rubric

The assessment produces separate competency scores for independent and AI-assisted engineering.

### Stage A — Independent Engineering

| Competency               | Weight |
| ------------------------ | ------ |
| Root-cause analysis      | 25%    |
| Concurrency correctness  | 30%    |
| Transactional integrity  | 20%    |
| Testing and verification | 15%    |
| Engineering judgment     | 10%    |

### Stage B — AI-Assisted Engineering

| Competency                   | Weight |
| ---------------------------- | ------ |
| Implementation correctness   | 30%    |
| AI output evaluation         | 25%    |
| Verification discipline      | 20%    |
| Architecture and reliability | 15%    |
| Technical ownership          | 10%    |

Provisional rubric weights for pilot calibration, not validated psychometric weights. Technical defense supplies evidence to the relevant dimensions rather than a third combined score.

Each competency receives a behaviorally anchored rating from 1 to 5, or Insufficient Evidence.

A reviewer must cite specific artifacts supporting each rating, such as a test result, code change, explanation, or technical defense answer.

Passing tests alone must not produce an automatic senior-level rating.

## 9. Reviewer guide and hidden assessment materials

Candidate-facing instructions and evaluator-only materials must be separated.

The reviewer package should contain:

- A reference implementation for each stage.
- Seeded defect descriptions and expected failure mechanisms.
- Deterministic visible and hidden tests.
- Acceptable alternative implementation strategies.
- Rubric anchors and examples of strong and weak evidence.
- Known false positives and environmental failure cases.
- Guidance for handling incomplete submissions.
- A transcript-review procedure.
- A calibration set for comparing reviewer consistency.

### Critical implementation detail

Stage A and Stage B must have independent scoring evidence.

The Stage B result should not automatically erase a Stage A failure, nor should an incomplete Stage A prevent a candidate from demonstrating AI-assisted competence.

For reproducibility, preserve an immutable snapshot at the end of Stage A. Stage B can continue from the candidate's code, but reviewers need to distinguish inherited defects from new changes.

The pilot should also investigate whether Stage B becomes disproportionately difficult for candidates who did not complete Stage A. If so, use a standardized transition baseline or separately calibrated variants.

## 10. Pilot acceptance criteria

Assessment 001 is ready for an employer-facing pilot when:

- The starter repository launches reliably in an isolated environment.
- Seeded defects are reproducible.
- All visible and hidden tests have been independently verified.
- Concurrent tests are deterministic enough for reliable grading.
- Stage transitions preserve code and evidence correctly.
- The AI assistant's permissions and model configuration are recorded.
- Reasoning transcripts align with engineering events.
- Microphone failure does not silently invalidate the assessment.
- The reviewer can evaluate both stages independently.
- At least three technically qualified pilot participants complete the assessment.
- Two reviewers can apply the rubric and discuss disagreements using specific evidence.
- Candidate feedback indicates that instructions, time limits, and environment are reasonably clear.

## 11. Proposed implementation sequence

Milestone 1 — Assessment repository

Implement the OrderFlow service, database schema, seed data, seeded defects, and test suite. Verify the reference solutions independently.

Milestone 2 — Candidate execution experience

Provide an isolated coding environment, stage timers, test execution, code snapshots, and controlled AI access.

Milestone 3 — Live reasoning capture

Add microphone permission, transcription, event timestamps, secure persistence, and transcript review.

Milestone 4 — Reviewer evaluation

Build the evidence timeline, rubric interface, and structured assessment report.

Milestone 5 — Pilot calibration

Run supervised trials, evaluate task difficulty, compare reviewer assessments, and revise the protocol.

## 12. Product decision

## Assessment 001 — Specification status

Conceptual design complete

Executable repository not yet implemented

Reference solutions and tests not yet validated

Rubric and timing require pilot calibration

Assessment 001 is now defined as a senior-level backend reliability exercise combining independent debugging, AI-assisted implementation, and live reasoning capture.

The next engineering task is to implement and validate the OrderFlow repository, including the two seeded Stage A defects and Stage B idempotency requirements. That will give Synapse Assess its first executable assessment before investing in the broader platform.