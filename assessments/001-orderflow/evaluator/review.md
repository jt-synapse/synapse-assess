# OrderFlow reviewer guide · v1.0.0

Use the immutable Stage A snapshot to assess independent work and the Stage B snapshot and its diff to assess AI-assisted work. Keep separate results when an inherited defect affects Stage B. Ask the versioned defense questions and allow written answers. Cite the timestamp, snapshot, test record or answer supporting each judgment. Preserve disagreements and corrections.

## Defects and reference implementations

The starter reads stock before it writes an absolute new quantity. Two transactions can both read one available unit and commit distinct reservations. Its early commit also leaves a reservation behind when the inventory update fails. The independent reference uses a conditional update and one transaction for allocation and insertion. A correct row lock or another database-enforced solution can also satisfy the contract.

The assisted reference adds a transaction-scoped key lock and an immutable mapping to the committed reservation. Verify persistence across workers and process restarts. A unique constraint with an appropriate wait/replay path is another valid approach. Passing tests establishes observed outcomes for those inputs. Review the implementation and its explained assumptions as additional evidence.

## Rubric and examples

| Independent competency | Weight | Example evidence |
| --- | ---: | --- |
| Root-cause analysis | 25% | An interleaving explains the two successful requests |
| Concurrency correctness | 30% | Snapshot and competing-transaction test establish the stock invariant |
| Transactional integrity | 20% | Forced database failure leaves no reservation or stock delta |
| Testing and verification | 15% | A regression test isolates the symptom |
| Engineering judgment | 10% | Defense explains the lock and its tradeoffs |

| AI-assisted competency | Weight | Example evidence |
| --- | ---: | --- |
| Implementation correctness | 30% | Equivalent retries recover the same committed ID |
| AI output evaluation | 25% | A specific suggestion was checked and accepted, changed or rejected |
| Verification discipline | 20% | Concurrent retries and a restart were exercised |
| Architecture and reliability | 15% | Candidate accounts for durable ordering and failed transactions |
| Technical ownership | 10% | Defense links a design decision to a failure mode and test |

Apply the 1–5 anchors per competency. A 1 requires evidence of behavior that violates the relevant invariant. A 2 supports part of the requirement but leaves a demonstrated failure. A 3 meets the requirement with cited verification. A 4 also explains relevant edge cases and tests them. A 5 supports a reasoned comparison of alternatives and validates the chosen guarantee under failure or concurrency. Use *Insufficient Evidence* when the material cannot support an anchor. The weights and anchors are provisional until the supervised pilot.

For calibration, independently review (1) the starter with a correct spoken root-cause analysis and failing invariants, (2) the Stage A reference with no accompanying explanation, and (3) the Stage B reference with a recorded restart check and a justified rejection of a process-local cache. Compare ratings against cited evidence. A correct artifact alone supplies no evidence of AI output evaluation. A missing explanation may be supplied through defense or written reasoning. Verify transcript quotes against corrections and note ambiguities. Exclude vocal traits and speaking frequency from ratings.

Mark setup outages, database lock timeouts and transport failures as environmental interruptions when evidence does not establish a candidate defect. Preserve the run log and rerun the sealed artifact on a fresh evaluator. An incomplete submission can still support individual competency ratings. Defense contributes to the two stage ratings. Reviewers document the limits of the controls actually observed.
