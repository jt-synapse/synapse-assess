Added to the Synapse Assess future feature roadmap.

### Feature F-002: Candidate Feedback & Development Loop

Future Phase — Post-MVP

Concept: After completing an assessment, candidates receive personalized, actionable feedback based on their code, debugging process, AI interactions, and spoken reasoning transcript.

The system would provide:

1. Code Quality Review — Correctness, maintainability, testing, architecture, and missed edge cases.
2. Reasoning Analysis — Compare verbal explanations with actual implementation decisions and observed behavior.
3. AI Usage Feedback — Evaluate how effectively the candidate directed, verified, and challenged AI-generated solutions.
4. Strengths & Weaknesses — Identify demonstrated competencies and areas requiring improvement.
5. Personalized Learning Recommendations — Suggest concepts, exercises, and resources based on assessment evidence.
6. Progress Tracking — Compare performance across future assessments to demonstrate improvement.

### Example candidate feedback

> Strength: You correctly identified the concurrency issue and explained why the inventory update needed to be atomic.
>
> Improvement opportunity: Your implementation addressed concurrent requests, but your tests did not cover transaction rollback failures.
>
> Recommended practice: Explore PostgreSQL transaction isolation levels and write tests for partial database failures.

### Strategic significance

This introduces an interesting second dimension to Synapse Assess:

- For employers: Evidence-based hiring decisions.
- For candidates: A technical development tool that helps them understand and improve their engineering abilities.

Eventually, this could support a continuous learning and assessment platform, rather than a one-time interview product.

Priority: Post-MVP. We'll preserve it for future product planning without expanding the current implementation scope.

One important design principle: candidate feedback should be developmental, not simply a disclosure of proprietary hiring scores or hidden test cases. It should also distinguish demonstrated weaknesses from areas where the assessment collected insufficient evidence.