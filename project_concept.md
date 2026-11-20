# SynapseFaster — Hybrid Technical Assessment Platform

Founding Product Blueprint · Version 1.0 · November 2026

Operating entity: SynapseFaster LLC\
Product working name: Synapse Assess\
Business model: B2B SaaS, employer-sponsored technical assessments\
Initial market: US-based engineering organizations and specialized technical recruiting firms\
Initial specialty: Senior backend and full-stack software engineers\
Stage: Pre-validation, product definition

## 1. Executive decision

SynapseFaster will develop an evidence-based technical assessment platform that evaluates two distinct dimensions of modern software engineering:

1. Independent engineering competence: What can a candidate understand, diagnose, design, and implement without generative AI assistance?
2. AI-assisted engineering competence: How effectively can that same candidate use AI tools to solve engineering problems while maintaining technical judgment, correctness, security, and ownership of the resulting work?

The platform will evaluate these dimensions separately before producing a unified, evidence-backed candidate report.

This separation is the central product thesis.

A candidate who performs well with AI but struggles to reason independently is not equivalent to a candidate who demonstrates strong foundational understanding and effective AI collaboration. Conversely, an engineer who performs exceptionally without AI but struggles to use modern development tools may have a different competency profile.

The platform will reveal those differences without assuming that either profile is universally superior.

The employer determines the relative importance of each competency based on the actual position.

## The core product experience

Stage A

### Independent Engineering

Unaided code comprehension, debugging, implementation, and technical reasoning.

AI disabled

Stage B

### AI-Assisted Engineering

Problem solving with a provided AI assistant, including verification and critical evaluation of its output.

AI permitted

Evidence-Based Engineering Profile

Separate scores, observed behaviors, code artifacts, and employer-specific interpretation

### Founding principles

- Assess engineering capability rather than memorized algorithms.
- Measure independent reasoning and AI-assisted performance as separate constructs.
- Use realistic engineering work rather than abstract puzzles wherever feasible.
- Produce auditable evidence rather than opaque hiring recommendations.
- Preserve candidate privacy and support reasonable accommodations.
- Make assessments job-related, reproducible, and consistently scored.
- Keep employers responsible for final hiring decisions.
- Avoid claiming that remote environments can be proven completely AI-free.

## 2. Target market and initial wedge

The platform will not launch as a general-purpose competitor to HackerRank, CodeSignal, or CoderPad.

Its initial market will be organizations hiring experienced engineers for positions where code comprehension, debugging, architectural judgment, and responsible AI usage are important.

### Ideal customer profile

| Attribute                | Initial target                                                                               |
| ------------------------ | -------------------------------------------------------------------------------------------- |
| Organization             | 50–1,000 employees                                                                           |
| Engineering organization | 10–200 engineers                                                                             |
| Hiring activity          | Recurring senior engineering vacancies                                                       |
| Buyer                    | VP Engineering, Head of Engineering, technical recruiting leader                             |
| Primary user             | Hiring manager or senior technical interviewer                                               |
| Initial roles            | Senior backend and full-stack engineers                                                      |
| Primary pain             | Difficulty distinguishing demonstrated engineering judgment from polished AI-assisted output |

These are proposed segmentation criteria, not validated market boundaries.

### Beachhead customer

I would prioritize engineering organizations that already conduct practical technical interviews but lack a consistent way to evaluate candidates' AI-assisted development practices.

They have an existing workflow to improve. You are not asking them to invent a new hiring philosophy.

Technical recruiting firms become a secondary distribution channel after the assessment workflow has been validated with direct employers.

## 3. The assessment protocol

I recommend an initial 90-minute assessment with three stages: independent work, AI-assisted work, and technical defense.

The third stage is essential. Without it, you risk collecting code artifacts without establishing whether the candidate understands their own solution.

## Proposed assessment timeline

Stage A

35 min

Stage B

40 min

Defense

15 min

0 min35 min75 min90 min

Provisional format to validate against candidate completion rates, reviewer burden, and role relevance. Onboarding and breaks must be accommodated separately or explicitly budgeted.

### Stage A — Independent Engineering (35 minutes)

Objective: Measure what the candidate can accomplish without generative AI.

The candidate receives an unfamiliar but manageable software repository with a realistic defect and a limited implementation task.

Example scenario: A FastAPI service processes customer orders, but certain concurrent requests produce inconsistent inventory reservations.

The candidate must:

1. Explore the relevant code and explain the system's behavior.
2. Reproduce and diagnose a defect.
3. Implement a targeted fix.
4. Write or update tests.
5. Explain the reasoning behind the chosen solution.

Permitted: Local documentation bundled with the assessment, tests, debugging tools, and standard IDE functionality.

Not permitted: Generative AI assistants, external communications, or external solution services.

The platform can restrict its own provided environment, but it cannot conclusively establish that an unsupervised remote candidate has no external assistance. The report must distinguish verified controls from policy compliance declarations.

### Stage B — AI-Assisted Engineering (40 minutes)

Objective: Measure the candidate's ability to direct, evaluate, and integrate AI-generated work.

The candidate receives a related but independently scored engineering requirement.

Example: Extend the order service to support idempotent requests, meaningful error handling, and a new performance constraint.

The platform provides a controlled AI assistant with a documented model version and defined tool access.

The candidate may use the assistant to investigate the codebase, propose changes, generate tests, or discuss implementation strategies.

The evaluation focuses on whether the candidate:

- Frames useful requests and supplies relevant context.
- Identifies incorrect or unsafe AI suggestions.
- Validates generated code through testing and inspection.
- Maintains ownership of design decisions.
- Recognizes trade-offs and failure modes.
- Produces correct, maintainable work.

Important: Prompt volume, token consumption, and number of AI interactions should not be treated as direct measures of engineering competence.

An effective engineer may require fewer AI interactions than a less experienced engineer.

### Stage C — Technical Defense (15 minutes)

Objective: Establish whether the candidate understands the implementation and can reason about changed requirements.

The candidate responds to three follow-up questions based on their work.

Examples:

- What happens if two requests update the same inventory record simultaneously?
- How would your solution change if the service processed ten times more traffic?
- Which AI-generated suggestion did you reject, and why?

For the MVP, the defense should be conducted or reviewed by a qualified human evaluator.

I would not initially allow an LLM to independently determine whether a candidate's explanation is sufficiently credible.

## 4. A critical assessment-design decision

There is a methodological problem with using Stage A and Stage B scores to calculate a simple AI productivity improvement percentage.

The tasks are not necessarily equivalent.

A candidate's Stage B performance could improve because the task is easier, because they learned the repository during Stage A, or because AI assistance was useful.

Therefore:

Do not calculate an "AI uplift score" by simply subtracting Stage A from Stage B.

The MVP should report separate competency profiles.

Later, if you want to measure causal improvement from AI assistance, you would need a controlled evaluation design using calibrated tasks, counterbalancing, and comparable difficulty.

That distinction matters if you intend to sell scientifically defensible hiring assessments.

## 5. Competency framework and scoring

I recommend a multidimensional rubric rather than one universal candidate score.

## Competency model

| Independent competency     | AI-assisted competency      |
| -------------------------- | --------------------------- |
| Code comprehension         | Problem framing and context |
| Root-cause analysis        | AI output evaluation        |
| Implementation correctness | Verification and testing    |
| Engineering judgment       | Tool orchestration          |
| Testing and debugging      | Technical ownership         |

Each dimension uses a behaviorally anchored 1–5 rubric, with an explicit Insufficient Evidence option.

| Rating | Interpretation                                         |
| ------ | ------------------------------------------------------ |
| 1      | Does not demonstrate the required competency           |
| 2      | Partial understanding; substantial gaps                |
| 3      | Meets the defined role-level expectation               |
| 4      | Strong performance with sound technical judgment       |
| 5      | Exceptional performance supported by specific evidence |

The numeric scale must be defined separately for each competency and seniority level. A score of 4 in debugging cannot automatically be treated as equivalent to a score of 4 in architecture.

### Example employer report

### Engineering Assessment Report

Illustrative candidate · Senior Backend Engineer

Example

Independent competency

# 3.8 / 5

Illustrative rubric aggregate

AI-assisted competency

# 4.4 / 5

Illustrative rubric aggregate

Competency evidence

Root-cause analysis

4/5

Implementation correctness

4/5

AI output evaluation

5/5

Verification discipline

4/5

Architectural judgment

3/5

Technical evidence

Identified a race condition, implemented an atomic update strategy, rejected an AI-generated workaround that weakened consistency guarantees, and supplied regression tests.

Recommended employer follow-up

Investigate experience with distributed transactions and production incident response.

All values and observations are fictional. Aggregate scores are for presentation only; production scoring requires validated weights and rubric calibration.

### Scoring governance

The system must distinguish three categories of evidence:

- Deterministic: Test outcomes, build results, execution status, and code diffs.
- Interpretive: Reviewer assessments of reasoning, maintainability, and architectural judgment.
- Contextual: AI interactions, time allocation, tool usage, and environment events.

Contextual evidence should inform review, not automatically reduce scores.

The initial product should never issue a universal "hire" or "reject" decision.

## 6. Product requirements

### MVP functional scope

| Capability                                  | Priority | MVP decision |
| ------------------------------------------- | -------- | ------------ |
| Employer organizations and RBAC             | P0       | Build        |
| Assessment templates and versions           | P0       | Build        |
| Candidate invitation and session management | P0       | Build        |
| Browser-based coding workspace              | P0       | Build        |
| Isolated code execution and tests           | P0       | Build        |
| Controlled AI assistant                     | P0       | Build        |
| Stage transitions and timers                | P0       | Build        |
| Git diffs and test evidence                 | P0       | Build        |
| Structured reviewer rubric                  | P0       | Build        |
| Employer report                             | P0       | Build        |
| Audit logging                               | P0       | Build        |
| Identity verification integrations          | P1       | Later        |
| Live interviewer collaboration              | P1       | Later        |
| ATS integration                             | P1       | Later        |
| Assessment template marketplace             | P2       | Defer        |
| Physical interview pods                     | P2       | Defer        |
| Candidate portable credentials              | P2       | Defer        |
| Automated hiring recommendations            | Excluded | Not planned  |

P0 means required for the first commercial pilot, not necessarily required for the first clickable prototype.

### Nonfunctional requirements

The system must provide:

- Tenant isolation across employer organizations.
- Reproducible assessment environments and immutable assessment versions.
- Short-lived execution environments with CPU, memory, runtime, and network limits.
- No candidate code execution on the application server.
- Scoped secrets and restricted access to AI provider credentials.
- Reliable recovery from browser disconnection.
- Explicit data-retention and deletion policies.
- Accessibility and reasonable-accommodation workflows.
- Human review and correction of evaluation reports.
- Transparent disclosure of monitoring and collected evidence.

An assessment environment must be disposable without losing authorized submitted work or the necessary audit evidence.

## 7. Technical architecture

I would separate the platform into a control plane, execution plane, and evaluation plane.

### Recommended technology stack

| Layer               | Technology                                      |
| ------------------- | ----------------------------------------------- |
| Frontend            | Next.js, React, TypeScript                      |
| Coding interface    | CodeMirror 6 initially                          |
| Backend             | FastAPI, Python                                 |
| Primary database    | PostgreSQL                                      |
| Background jobs     | Celery or managed queue                         |
| Execution isolation | Managed ephemeral sandbox provider              |
| Object storage      | S3-compatible storage                           |
| AI integration      | Provider-neutral LLM gateway                    |
| Authentication      | OIDC-based authentication and organization RBAC |
| Observability       | OpenTelemetry, structured logs, error tracking  |
| Deployment          | Managed cloud infrastructure initially          |

Avoid Kubernetes, custom hypervisor orchestration, or a proprietary remote desktop system in the MVP.

### Core domain model

The initial data model should include:

`Organization`, `User`, `Membership`, `RoleProfile`, `AssessmentTemplate`, `AssessmentVersion`, `AssessmentInvitation`, `Candidate`, `AssessmentSession`, `StageAttempt`, `WorkspaceSnapshot`, `ExecutionResult`, `AIInteraction`, `EvidenceEvent`, `Rubric`, `RubricScore`, `ReviewerDecision`, `AssessmentReport`, and `AuditEvent`.

Each assessment session should reference immutable versions of its task, rubric, sandbox image, and AI policy.

This enables reproducibility and makes historical reports interpretable even after the assessment changes.

### AI-assisted execution controls

The platform should provide the AI assistant through its own gateway.

That enables controlled model access, usage metering, tool permissions, and reproducible session configuration.

The gateway should record the model identifier, model configuration, tool invocations, timestamps, and relevant interactions, subject to disclosed privacy and retention policies.

Do not assume that recording AI prompts is sufficient to establish whether the candidate understood the response.

Understanding is assessed through the work and technical defense.

## 8. Security and integrity architecture

I would define four assurance levels rather than one universal "verified" designation.

| Level | Environment                | Assurance claim                                          |
| ----- | -------------------------- | -------------------------------------------------------- |
| L0    | Standard remote browser    | Candidate declaration and submitted work                 |
| L1    | Managed cloud workspace    | Controlled execution and AI tools within the workspace   |
| L2    | Supervised remote session  | Additional identity and observation controls             |
| L3    | Approved physical location | Documented in-person identity and environment procedures |

No level guarantees the absence of undisclosed assistance.

The assessment report should state the actual controls applied, any exceptions, and any material gaps in evidence.

For the MVP, I would support L0 and L1, with the architecture designed to accommodate higher-assurance options later.

### Data protection

Candidate source code, assessment answers, AI conversations, and reviewer observations may contain sensitive personal or employer information.

Use encryption in transit and at rest, strict organization-level authorization, short-lived access credentials, explicit retention windows, and audit trails for report access.

Do not train models on candidate assessment data by default. Any secondary use requires an appropriate legal basis, contractual authorization, and transparent disclosure.

## 9. Business model and unit economics

The initial business should be employer-sponsored.

I would test usage-based pricing before committing to annual subscriptions.

## Illustrative assessment economics

Assessment price$149

Compute, sandbox and AI cost$12

Human review time15 min

Fully loaded reviewer hourly cost$90/hr

Contribution per assessment

# $109.50

Contribution margin

# 73.5%

Includes an assumed $5 processing/support allowance. Excludes fixed engineering, sales, legal, content development, taxes, and customer acquisition. All inputs are hypothetical.

This reveals a fundamental business constraint.

A $49 assessment with substantive human review may be commercially unattractive.

A $149 assessment could support a stronger contribution margin, but the buyer must perceive enough value to pay that price.

I would not lock in pricing until employer discovery and pilot usage provide evidence.

## 10. Go-to-market strategy

### Initial commercial proposition

> Synapse Assess helps engineering teams evaluate how candidates solve real software problems independently and with AI assistance, producing structured technical evidence that hiring managers can review and defend.

The initial sales motion should be founder-led.

Target employers with active senior engineering openings, existing practical interview processes, and a stated concern about the quality of technical hiring signals.

### Pilot structure

Offer a limited paid pilot covering five assessments for one role family, with defined support, a structured feedback review, and a clear evaluation of whether the platform improved the hiring team's process.

The pilot should measure:

- Whether hiring managers found the evidence actionable.
- Whether the assessment changed or clarified follow-up questions.
- Candidate completion and withdrawal rates.
- Reviewer time per assessment.
- Technical reliability and per-session costs.
- Willingness to purchase additional assessments.

Do not rely solely on customer satisfaction surveys. Observe whether employers actually incorporate the evidence into their decisions.

## 11. Validation and execution roadmap

Phase 0 — Discovery and assessment design (Weeks 1–3)

Interview 20 prospective buyers. Select one role family, define competency rubrics, draft two equivalent assessment variants, and recruit technical reviewers.

Gate: Three to five employers agree to evaluate the prototype against real hiring needs.

Phase 1 — Research prototype (Weeks 4–6)

Build one functioning repository-based assessment with independent and AI-assisted stages. Conduct supervised trials and review the evidence manually.

Gate: The workflow runs reliably, produces interpretable results, and identifies clear employer value.

Phase 2 — Commercial MVP (Weeks 7–12)

Add employer accounts, invitations, persistent sessions, rubric review, report generation, basic billing, and production-grade execution isolation.

Gate: Two organizations pay for assessments and express credible repeat-purchase intent.

Phase 3 — Product validation (Months 4–6)

Improve reliability, add additional assessment variants, measure reviewer agreement, and validate pricing.

Gate: Recurring paid usage, acceptable contribution margins, and evidence that customers prefer the workflow to existing alternatives.

These are target timelines, not guaranteed delivery dates. A single founder should prioritize product reliability and paid validation over completing every feature on schedule.

## 12. Investment risks and mitigation

| Risk                               | Severity | Response                                 |
| ---------------------------------- | -------- | ---------------------------------------- |
| Established assessment competitors | Critical | Narrow role-specific differentiation     |
| Unproven assessment validity       | Critical | Human calibration and outcome research   |
| Employer acquisition difficulty    | Critical | Founder-led paid design partnerships     |
| Candidate burden                   | High     | Time limits, accessibility, relevance    |
| AI policy circumvention            | High     | Transparent assurance levels             |
| Untrusted code execution           | Critical | Managed sandbox isolation                |
| Human review costs                 | High     | Evidence-driven reviewer workflows       |
| AI model variability               | High     | Versioning and controlled configurations |
| Assessment content leakage         | High     | Version rotation and task variants       |
| Weak recurring demand              | Critical | Paid pilot and repeat-purchase gates     |

One further risk deserves attention: a candidate's performance on an unfamiliar codebase may reflect prior exposure to the language, framework, or development environment rather than general engineering competence.

Assessment tasks must be aligned with the role, and reviewers must avoid overgeneralizing from one short exercise.

## 13. What is explicitly out of scope

To protect the company from premature complexity, I would exclude the following from the initial product:

- Physical interview pods and coworking partnerships.
- Wearable detection and RF monitoring.
- Candidate-paid certification.
- A public candidate ranking marketplace.
- Automated hiring decisions.
- A proprietary AI foundation model.
- Full-featured cloud IDE development.
- A large assessment question bank.
- Multi-language support before validating the first ecosystem.
- Enterprise ATS integrations before customer demand justifies them.

These exclusions are deliberate strategic constraints, not missing features.

## 14. Founding business assumptions

The following assumptions must be tested before major capital or engineering commitments.

| Hypothesis                                                  | Required evidence                        |
| ----------------------------------------------------------- | ---------------------------------------- |
| Employers value separate independent and AI-assisted scores | Buyer interviews and paid usage          |
| Realistic engineering tasks provide useful hiring signals   | Reviewer feedback and validation studies |
| Employers will pay a premium for structured evidence        | Paid pilots                              |
| Candidates will complete a 90-minute assessment             | Completion and withdrawal data           |
| Human review can be economically sustainable                | Measured reviewer time and cost          |
| AI-assisted evaluation is meaningfully differentiated       | Competitive trials and repeat purchases  |
| Employers will integrate reports into their process         | Observed workflow adoption               |

## 15. Founding decisions

## Product Definition — v1.0

| Company               | SynapseFaster LLC                               |
| --------------------- | ----------------------------------------------- |
| Product               | Synapse Assess (working name)                   |
| Category              | Technical assessment infrastructure             |
| Core innovation       | Independent + AI-assisted competency evaluation |
| Initial buyer         | Engineering hiring teams                        |
| Initial role          | Senior backend/full-stack engineer              |
| Business model        | Employer-sponsored B2B SaaS                     |
| Assessment duration   | 90-minute proposed protocol                     |
| Initial delivery      | Browser-based managed workspace                 |
| Human oversight       | Required for interpretive scoring               |
| Physical verification | Optional future capability                      |
| Current stage         | Pre-validation                                  |

## Final investment assessment

Verdict: Conditional GO for discovery and prototype development. Not yet ready for full commercial buildout or outside investment.

The hybrid model is more strategically interesting than the original physical interview-pod concept. It addresses a problem that is likely to remain relevant as AI becomes embedded in software engineering workflows: employers need to distinguish foundational engineering knowledge from effective AI-assisted execution.

However, the business will succeed only if SynapseFaster can demonstrate that this distinction improves actual hiring decisions enough for employers to pay.

The strongest near-term opportunity is not a comprehensive technical hiring platform. It is a focused assessment workflow that produces evidence hiring managers cannot easily obtain from existing interviews.

### Recommended next decision

Before designing the full implementation, I would formalize the first assessment itself: its repository, defects, implementation requirements, AI assistant permissions, technical defense, rubrics, and evidence capture.

That single assessment will serve as both the technical proof of concept and the product used in customer discovery.

It will also expose whether the hybrid evaluation thesis works in practice before you commit to building an entire SaaS platform.

The next milestone should be one credible, repeatable hybrid assessment—not a completed platform.

# Synapse Assess — Live Reasoning Capture

Feature proposal: Live microphone capture, speech-to-text transcription, and contextual reasoning analysis during technical assessments.

I would add this as a core feature of the hybrid assessment platform. It could provide valuable evidence that traditional coding assessments often miss: how candidates explain their engineering decisions while actively solving problems.

The objective is not simply to record speech. It is to connect a candidate's explanations to the code changes, test executions, AI interactions, and decisions occurring at the same time.

## 1. Candidate experience

During the coding assessment, the platform requests microphone permission and explains that the candidate should narrate their reasoning as they work.

The microphone records spoken explanations and converts them into timestamped text.

### Technical Assessment Workspace

Stage A · Independent Engineering

&#x20;Recording

Reasoning Transcript

Live transcription

04:12

"I'm checking how the inventory update works because the failing test suggests two requests are modifying the same record."

06:38

"The update isn't atomic. I'll change the transaction boundary and add a concurrency test to verify the fix."

09:21

"The test passes now, but I also need to check what happens when the transaction fails halfway through."

Microphone enabled · Transcript saved with assessment

Illustrative interface and transcript, not an active microphone or recording session.

### Candidate instructions

At the beginning of the assessment, display:

> As you work, explain your reasoning aloud. Describe what you're investigating, why you're making changes, how you're validating your solution, and any trade-offs you're considering. You do not need to speak continuously. Your explanations will be transcribed and associated with your assessment for technical review.

The final sentence is important. Candidates should not feel obligated to narrate every keystroke.

## 2. Why this is valuable

Consider two candidates who both produce a working solution.

Candidate A identifies the root cause, explains the trade-offs, implements a fix, and validates it.

Candidate B produces similar code but provides little evidence of understanding.

The transcript can help an evaluator investigate those differences.

However, silence is not evidence of incompetence, and articulate speech is not necessarily evidence of stronger engineering ability.

I would use verbal explanations as supporting evidence, not an independent score for talkativeness or communication style.

## 3. Connect speech to engineering events

This is where the feature becomes substantially more valuable.

Instead of storing one large transcript, capture timestamped segments and associate them with relevant engineering events.

### Unified Assessment Timeline

- 04:12 · Spoken reasoning

  "I think the problem is in the inventory transaction."
- 04:35 · Code inspection

  Opened `inventory_service.py` and examined the update function.
- 06:38 · Spoken reasoning

  "I'll make the operation atomic and test concurrent requests."
- 08:10 · Code change

  Updated transaction logic and added a regression test.
- 09:05 · Test execution

  Concurrency test passed.

Example timeline showing correlated observations, not proof of the candidate's internal reasoning.

This creates a structured record of what the candidate said, what they changed, and what they tested.

The reviewer can examine whether the explanation is consistent with the observed work.

## 4. Technical architecture

I would implement the feature as a dedicated Reasoning Capture Service integrated with the assessment session.

### Proposed implementation

| Component          | Responsibility                                        |
| ------------------ | ----------------------------------------------------- |
| Browser capture    | Request microphone permission and capture audio       |
| Audio transport    | Stream or upload short audio chunks securely          |
| Speech-to-text     | Produce timestamped transcript segments               |
| Event alignment    | Associate speech with code, tests, and AI events      |
| Transcript storage | Persist text, timestamps, and provenance              |
| Reviewer interface | Display searchable transcripts alongside code changes |
| Retention controls | Delete audio and transcripts according to policy      |

For the initial MVP, I would use a managed speech-to-text service rather than building a transcription model.

Audio should be encrypted in transit. The platform should buffer recordings during temporary network interruptions and clearly indicate capture failures.

### Suggested data model

```
class ReasoningSegment:    id: UUID    assessment_session_id: UUID    stage_attempt_id: UUID    start_ms: int    end_ms: int    transcript_text: str    transcription_confidence: float | None    source_audio_id: UUID | None    related_event_ids: list[UUID]    transcription_model: str    created_at: datetime
```

I would also include a `TranscriptCorrection` record so candidates or authorized reviewers can flag transcription errors without silently modifying the original evidence.

## 5. How this works in the hybrid assessment

| Stage                       | Reasoning capture                                                             |
| --------------------------- | ----------------------------------------------------------------------------- |
| A — Independent Engineering | Candidate explains diagnosis, implementation choices, and tests               |
| B — AI-Assisted Engineering | Candidate explains why they request, accept, reject, or modify AI suggestions |
| C — Technical Defense       | Candidate answers targeted questions about the completed work                 |

Stage B is particularly interesting.

For example, the AI assistant proposes a solution that passes the visible tests but introduces a concurrency defect.

A candidate who says, "This solution passes the test, but the shared state isn't protected, so I'm going to revise it," demonstrates evidence of critical evaluation.

That is a stronger signal than merely observing that the candidate accepted or rejected an AI suggestion.

## 6. Privacy, fairness, and accessibility requirements

I would make five requirements mandatory:

1. Explicit recording notice and consent: Explain what is recorded, why, who can access it, and how long it is retained. Account for applicable recording-consent laws.
2. Accessible alternatives: Provide a comparable written-reasoning option or approved accommodation where appropriate.
3. No accent or fluency scoring: Evaluate technical substance, not speaking speed, accent, pronunciation, or verbosity.
4. No emotion or personality inference: Do not infer confidence, honesty, intelligence, or deception from vocal characteristics.
5. Minimal retention: For the MVP, consider deleting raw audio after transcription quality checks and a short correction window, retaining only the authorized transcript and evidence links.

The platform should not penalize candidates simply because they think silently. Instead, it can issue occasional optional reasoning prompts at meaningful checkpoints.

For example:

> What are you investigating right now, and what evidence would confirm your hypothesis?

That is more useful than demanding continuous narration.

## 7. MVP acceptance criteria

I would consider the feature ready for pilot use when:

- A candidate can grant or deny microphone permission with clear disclosure.
- Recording status is always visible.
- Speech is transcribed with timestamps and associated with the correct assessment stage.
- Transcript segments survive temporary network interruptions without duplication or incorrect ordering.
- Reviewers can search transcripts and jump to related code or test events.
- Transcription errors can be flagged and corrected transparently.
- The system supports an accessible alternative to spoken narration.
- Audio and transcript deletion policies work and are auditable.
- Microphone failures do not silently invalidate an assessment.

## 8. Product decision

## Feature specification: RC-001

| Feature                | Live Reasoning Capture                 |
| ---------------------- | -------------------------------------- |
| Priority               | P0 — Core MVP                          |
| Input                  | Candidate microphone audio             |
| Output                 | Timestamped reasoning transcript       |
| Integration            | Assessment event timeline              |
| Assessment use         | Supporting technical evidence          |
| Raw audio              | Temporary, policy-controlled retention |
| Candidate alternatives | Written reasoning and accommodations   |

My recommendation is to make this a core capability of Synapse Assess, but not to build an automated speech-based candidate scoring system.

The valuable product is a synchronized engineering evidence timeline: what the candidate explained, what they implemented, how they used AI, and what the tests demonstrated.

That could become a meaningful differentiator if hiring managers find it more useful than traditional coding scores.