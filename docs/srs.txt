Tool Call Evidence Ledger
A Framework for Verifiable, Tamper-Evident Tool Use in Agentic Systems
Software Requirements Specification (SRS)Version 1.0 | 28 October 2026 | Research prototype specification
Document
Software Requirements Specification (SRS)
Project type
Research prototype / experimental evaluation
Primary guarantee
Traceability of claims to recorded tool outputs + tamper evidence
Status
Baseline specification; implementation details marked as design decisions where applicable

Document map
1. Purpose, scope and terminology
2. Product context and users
3. Functional requirements
4. Data requirements and interfaces
5. Non-functional requirements
6. Use cases and acceptance criteria
7. Verification, evaluation and roadmap
8. Constraints, assumptions and limitations
References

1. Purpose and scope
This SRS defines the required behaviour of the Tool Call Evidence Ledger research prototype. The system records tool interactions made during an agent session, protects the recorded sequence with a SHA-256 linear hash chain, and evaluates whether atomic claims in the agent's final answer are supported by the recorded tool outputs.
The system answers a closed-world question: “Is this claim supported by what the tools returned and what was recorded?” It does not independently establish that a tool's output is factually correct in the real world.
1.1 Goals
Record each tool invocation and its returned result as a structured ledger entry.
Detect post-recording modification, deletion, reordering or insertion of ledger entries by validating the hash chain.
Split an answer into atomic claims and classify each claim as SUPPORTED, UNSUPPORTED or PARTIALLY_SUPPORTED.
Prefer deterministic structured matching for direct numeric/entity claims and a fixed set of derived calculations; use an LLM judge only for unresolved semantic cases.
Provide a trace pointer to the supporting entry and field whenever possible.
Compare the hybrid verifier with two LLM-judge baselines under a labelled, reproducible evaluation.
1.2 In scope
Python-based research prototype with command-line execution and inspection; no GUI is required for the initial study.
SQLite persistence, SHA-256 hash chaining, canonical serialization, a small set of toy tools and an experiment runner.
Claim decomposition, direct matching, a fixed derived-operation set, judge fallback and claim-level reports.
Synthetic/controlled test scenarios with injected errors and a held-out second toy domain.
Tamper tests, metrics collection, run logs and reproducible instructions.
1.3 Out of scope
Proving the truth or quality of external tool results.
A production multi-tenant service, distributed consensus, blockchain, Merkle tree or configurable hash algorithm.
A web dashboard, Streamlit UI or React frontend in the initial research scope.
An exhaustive theorem prover for all mathematical derivations or every form of natural-language entailment.
Automatic remediation of unsupported claims beyond reporting/verdict generation.
Claims of complete prevention of hallucination or cryptographic non-repudiation without external anchoring/signatures.
1.4 Definitions
Term
Definition
Agent
Program/model that chooses and invokes tools and then generates a final answer.
Tool call
A named external function/API/database operation with input parameters and a returned output or captured error.
Evidence Ledger
Append-only logical sequence of structured tool-call records with hash-chain fields.
Atomic claim
A single proposition that can be assessed independently.
Direct claim
A claim that restates an entity, value or field from a tool output.
Derived claim
A claim requiring one of the explicitly implemented calculations, e.g. sum, ratio, percentage change or date delta.
Paraphrased claim
A claim expressing the meaning of evidence without an exact string match.
Tamper-evident
A change is detectable when verification is performed against a trusted expected chain head or independently preserved checkpoint.
Baseline A
LLM judge assessing claims without access to the tool trace.
Baseline B
LLM judge assessing claims with the full tool trace in context.
2. Product context and users
2.1 Intended users
User/actor
Primary need
Researcher/developer
Run scenarios, inspect entries, reproduce results and diagnose failures.
Agent/tool adapter
Submit invocation metadata and capture tool outputs/errors consistently.
Verifier pipeline
Consume ledger evidence and return claim-level verdicts with trace pointers.
Evaluator
Run labelled cases against all three systems and calculate metrics.
External tool
Return structured data, text, numeric values or an error.
2.2 System boundary
User/scenario -> Agent -> Tool adapter -> External toy tool                                  |                 |                                  +---- capture <---+                                          |                                   Evidence Ledger                                  (SQLite + SHA-256)                                          |Agent final answer -> Claim decomposer -> Per-claim verifier                                         |              |                                  Structured matcher   LLM judge                                         |              |                                         +---- verdict -+                                                |                              report: verdict + evidence pointer
2.3 Operating assumptions
Python is the primary implementation language; SQLite is the default persistent store.
A model API is required for the claim decomposer and judge fallback, unless deterministic test doubles are used in unit tests.
Tool outputs can be serialized into a stable representation. Unsupported objects must be converted through a documented adapter or rejected.
The evaluation uses 40–60 scenarios as a realistic initial target, not as a claim of statistical coverage.
A fixed set of derivations is supported initially: sum, ratio, percentage change and date difference. Any additional derivation must be documented and versioned.
3. Functional requirements
ID
Requirement
Description
Acceptance condition
FR-01
Session creation
The system shall create a unique session identifier before the first tool call.
A new session is isolated from other sessions.
FR-02
Tool-call capture
For every tool invocation, the system shall capture tool name, input parameters, raw/normalized output, timestamp, session ID and sequence number.
A successful call produces exactly one committed ledger entry.
FR-03
Error capture
The system shall record tool failures/timeouts as entries with error status and sanitized error details, where capture is possible.
A failed call is not silently omitted from the trace.
FR-04
Hash-chain creation
The system shall calculate each entry's SHA-256 hash over a deterministic canonical payload that includes the previous entry hash.
Changing a protected field invalidates the affected hash and subsequent chain validation.
FR-05
Append ordering
The system shall assign a monotonically increasing sequence number within a session and link each entry to the prior entry.
Validation detects missing, duplicated or reordered entries within the checked chain.
FR-06
Ledger verification
The system shall recompute each entry hash and check previous-hash links from the trusted starting point.
The report identifies the first invalid entry and reason.
FR-07
Claim decomposition
The system shall decompose the final answer into atomic claims using a fixed prompt and machine-readable output schema.
Malformed model output is rejected/retried safely and never trusted without validation.
FR-08
Direct matching
The system shall compare claim entities/numbers/values against structured fields in the trace using deterministic matching rules.
A match returns the exact entry ID and field path.
FR-09
Derived matching
The system shall evaluate a documented, finite set of calculations including sum, ratio, percentage change and date delta.
The calculation records its input evidence pointers and arithmetic rule.
FR-10
Judge fallback
If structured matching cannot decide a claim, the system shall pass the claim and relevant evidence to an LLM judge.
The judge returns a constrained verdict, rationale and evidence pointer or explicitly reports no supporting field.
FR-11
Three-way verdict
The system shall emit SUPPORTED, UNSUPPORTED or PARTIALLY_SUPPORTED for each claim.
Every answer claim has one verdict or a documented processing error.
FR-12
Evidence localization
The system shall attach one or more ledger-entry/field pointers to supported or partially supported claims when identifiable.
Pointers resolve to existing entries and fields.
FR-13
Baseline A
The evaluator shall run an LLM judge without tool trace access.
Baseline prompt/model settings are logged.
FR-14
Baseline B
The evaluator shall run an LLM judge with the full tool trace in context.
Uses comparable model and prompt style to hybrid fallback where feasible.
FR-15
Metrics
The evaluator shall calculate claim-level precision, recall, F1, localization accuracy, false-positive rate, latency and estimated cost.
Results are exported as CSV/JSON with run metadata.
FR-16
Tamper experiment
The test suite shall deliberately alter, remove and reorder stored entries and verify detection.
Tamper-detection outcomes are recorded, not assumed.
FR-17
Held-out domain
The experiment runner shall support a structurally different domain held out from matcher development.
Held-out cases are not used to tune matching rules.
FR-18
CLI inspection
The prototype shall provide commands to run a scenario, inspect a session, verify a chain and export results.
Commands and options are documented in the developer guide.
FR-19
Run reproducibility
The system shall record software version, model identifier, prompt/version identifier, scenario ID and timestamp for evaluation runs.
A result can be traced to the configuration that produced it.
FR-20
Privacy-aware logging
The system shall avoid logging secrets such as API keys and shall support redaction of sensitive tool inputs/outputs.
Redaction policy is documented and applied before persistence where configured.
4. Data requirements and interfaces
4.1 Ledger entry fields
Field
Type / example
Purpose
session_id
UUID/string
Separates independent sessions.
sequence_no
Integer, starts at 1
Deterministic order and gap detection.
entry_id
UUID or session_id + sequence
Stable evidence pointer.
timestamp_utc
ISO-8601 UTC
When the call was captured; not a trusted external timestamp by itself.
tool_name
String
Identifies the invoked tool.
input_json
JSON object
Captured parameters after secret redaction policy.
output_json
JSON/string/null
Tool return value in stable serializable form.
status
success/error/timeout
Distinguishes result from failure.
error_info
Optional structured object
Sanitized exception category/message.
previous_hash
64-hex SHA-256; genesis marker for first entry
Links to the preceding record.
entry_hash
64-hex SHA-256
Digest of canonical protected payload.
schema_version
String/integer
Makes payload format changes explicit.
Hash calculation contract: serialize the protected payload deterministically, including session ID, sequence number, timestamp, tool name, input, output, status, error metadata, schema version and previous_hash; then compute SHA-256 over the resulting UTF-8 bytes. The entry_hash field itself is excluded from the payload being hashed. Use a canonical JSON scheme (RFC 8785-compatible implementation) or a narrowly specified deterministic serializer with tests; do not rely on arbitrary dictionary ordering.
4.2 Suggested interface contracts
Interface
Input
Output
ToolAdapter.invoke(tool_name, args)
Tool identifier and JSON-compatible args
Tool result or captured error plus ledger entry ID
Ledger.append(entry_payload)
Protected entry fields excluding entry_hash
Persisted entry including entry_hash
Ledger.verify(session_id)
Session ID
valid/invalid, first failing sequence, reason, checked count
ClaimDecomposer.decompose(answer)
Final answer string
List of atomic claims with claim IDs and text
StructuredMatcher.match(claim, evidence)
Claim plus candidate structured fields
supported/unsupported/unresolved + evidence pointers + method
LLMJudge.assess(claim, evidence?)
Claim and optional trace
Constrained verdict + rationale + candidate evidence pointers
Verifier.verify(answer, session_id)
Answer and ledger session
Ordered claim-level verdicts and aggregate status
Evaluator.run(dataset, systems)
Dataset and system configs
Metrics table and per-case records
4.3 Output report
{  "session_id": "session-001",  "chain_integrity": {"status": "VALID", "entries_checked": 3},  "claims": [    {      "claim_id": "C1",      "text": "The lookup returned 42 records.",      "claim_type": "direct_numeric",      "verdict": "SUPPORTED",      "method": "structured_direct_match",      "evidence": [{"entry_id": "session-001:2", "field_path": "$.output.count"}],      "reason": "Claim value matches the recorded output field."    }  ]}
5. Non-functional requirements
ID
Requirement
Measure / test
NFR-01
Integrity
All valid test chains verify; each protected-field mutation in tamper suite is detected when checked against trusted chain head.
NFR-02
Determinism
Same canonical payload and previous hash yield the same SHA-256 digest across repeated runs.
NFR-03
Traceability
Every verifier verdict stores method and resolvable evidence pointers where applicable.
NFR-04
Reliability
A malformed tool output or LLM response results in a controlled error/fallback, not silent acceptance.
NFR-05
Reproducibility
Evaluation output includes versions, prompts, model IDs, seeds where applicable and scenario IDs.
NFR-06
Performance
Measure latency and cost per claim; establish empirical values instead of inventing a performance SLA.
NFR-07
Maintainability
Separate ledger, adapters, decomposition, matching, judge and evaluation modules.
NFR-08
Security
Secrets are not persisted in plain logs; tool output is treated as untrusted data and cannot change verifier instructions.
NFR-09
Explainability
Verdicts include short reasons, method names and evidence pointers.
NFR-10
Portability
Prototype runs on a standard Python environment with SQLite and documented dependencies.
6. Use cases and acceptance criteria
UC-01: Record a tool call
Agent requests a named tool with JSON-compatible inputs.
Adapter invokes the tool and captures success, failure or timeout.
Adapter applies redaction policy and constructs a stable entry payload.
Ledger calculates the entry hash using the prior entry hash and persists the record transactionally.
System returns the tool result to the agent and an entry ID for audit.
Acceptance: a test can retrieve the entry, verify its fields, recompute the hash and confirm its previous_hash points to the prior record.
UC-02: Verify a final answer
Verifier validates the ledger chain before trusting its evidence.
Claim decomposer creates atomic claims and validates the response schema.
For each claim, matcher searches relevant structured fields and attempts supported fixed derivations.
If unresolved, the judge assesses the claim with the appropriate evidence context.
Verifier emits one verdict per claim and includes trace pointers when available.
Report includes chain integrity status and does not label the answer fully verified if the chain is invalid.
UC-03: Evaluate the system
Load frozen labelled scenarios and gold claim labels.
Run Baseline A, Baseline B and the hybrid verifier on the same scenarios.
Save raw per-claim outputs, latency, estimated cost, model/config versions and errors.
Calculate precision, recall, F1, false-positive rate and localization accuracy by claim type.
Run the held-out domain and tamper suite; report limitations and failure cases.
6.1 Acceptance checklist
Each tool invocation creates a corresponding ledger record, including captured failures.
Mutation of output, input, timestamp, tool name, previous_hash or sequence/order is detected by verification in the defined threat model.
Claim results include supported/unsupported/partial labels and evidence field pointers where available.
Structured direct/derived matcher executes before judge fallback.
The three systems run on the same labelled scenarios and export comparable metrics.
At least 15–20 failure cases are manually categorized for the final research analysis, where feasible within the roadmap.
README documents installation, CLI commands, experiment execution and known limitations.
7. Verification and evaluation
7.1 Claim taxonomy
Type
Example
Primary evaluation expectation
Direct numeric/entity
Trace says count=42; answer says 42.
Deterministic field match should identify exact evidence.
Derived
Trace has old/new values; answer states percentage change.
Fixed operation must reproduce the result within a declared numeric tolerance.
Paraphrased
Trace says status='degraded'; answer says the service is experiencing reduced performance.
Semantic judge may be required; human-labelled evidence remains the reference.
7.2 Baselines
Baseline A — LLM judge with no tool trace. This estimates answer-only judgement and is not the primary baseline.
Baseline B — LLM judge with full tool trace. This is the primary comparator because it reflects the straightforward trace-aware approach.
Hybrid — same trace ledger plus deterministic structured matching first and LLM-judge fallback for unresolved claims.
7.3 Metrics
Claim-level precision, recall and F1 for supported versus unsupported claims; define treatment of partial claims explicitly before scoring.
Localization accuracy: fraction of claims for which the system identifies the correct evidence entry and field.
False-positive rate: unsupported claims incorrectly accepted as supported.
Breakdown by direct, derived and paraphrased claims.
Latency and estimated model/API cost per claim and per scenario.
Tamper-detection rate on a predeclared set of controlled corruptions.
Held-out-domain performance and categorized error analysis.
Important evaluation discipline: do not use the AgentHallu 11.6% or 41.1% values as a predicted score for this prototype. They measure a different task/benchmark. Report your own results with dataset size, annotation method and uncertainty/limitations.
8. Constraints, assumptions and limitations
A hash chain is tamper-evident, not automatically tamper-proof. An attacker able to rewrite the entire ledger and recompute every hash can create a self-consistent replacement unless a trusted chain head/checkpoint is stored independently.
The ledger verifies the integrity of recorded bytes/fields, not whether the tool output is true, fresh or authoritative.
Claim decomposition errors can propagate into matching and verdicts.
The structured matcher only supports the explicitly implemented operations; unsupported calculations fall back to the judge or remain unresolved.
LLM judge verdicts may be inconsistent, biased or vulnerable to prompt injection in tool output; treat trace content as data, not instructions.
A 40–60 scenario set and a small held-out domain are suitable for a student research prototype but limit broad generalization claims.
The system should avoid logging API secrets or unnecessary personal data; raw-output preservation must be balanced with redaction and research reproducibility.
8.1 Design decisions to freeze before implementation
Decision
Recommended default
Reason
Language
Python
Fast research iteration and available hashing, SQLite and testing libraries.
Persistence
SQLite
Simple, transactional, file-based store suited to a solo research prototype.
Hash
SHA-256, hard-coded
Standard digest; configurability does not advance the main research question.
Serialization
Canonical JSON / deterministic byte contract
Avoid different key order or whitespace creating different hashes.
Interface
CLI
Roadmap explicitly prioritizes experiments over a UI.
Tools
2–3 toy tools
Examples: calculator, lookup DB, fake weather or telecom-style lookup tools.
LLM
One chosen model for decomposition and judge where feasible
Reduces confounding when comparing systems.
Dataset
40–60 scenarios; second domain held out
Feasible scope with clear limitations.
References and research notes
Liu, X. et al. (2026). AgentHallu: Benchmarking Automated Hallucination Attribution of LLM-based Agents. EMNLP 2026. https://aclanthology.org/2026.emnlp-main.925/
NIST. Secure Hash Standard, FIPS PUB 180-4. https://csrc.nist.gov/pubs/fips/180-4/upd1/final
NIST CSRC. Hash Functions overview. https://csrc.nist.gov/projects/hash-functions
RFC 8785 (2020). JSON Canonicalization Scheme (JCS). https://www.rfc-editor.org/rfc/rfc8785.html
OWASP GenAI Security Project. OWASP Top 10 for LLM Applications 2026. https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/
Project source materials: user-provided project proposal, and uploaded Roadmap.pdf (scanned PDF; roadmap text extracted using OCR).
Evidence and interpretation note: AgentHallu's published numbers are background motivation only. They must not be presented as results from this project. The proposal's novelty statement is a project hypothesis to investigate, not an established universal claim. A literature review should confirm the final related-work and novelty wording before publication.