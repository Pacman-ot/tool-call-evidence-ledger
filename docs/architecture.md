Tool Call Evidence Ledger
A Framework for Verifiable, Tamper-Evident Tool Use in Agentic Systems
System Architecture and Design DocumentVersion 1.0 | 28 October 2026 | Research prototype specification
Document
System Architecture and Design Document
Project type
Research prototype / experimental evaluation
Primary guarantee
Traceability of claims to recorded tool outputs + tamper evidence
Status
Baseline specification; implementation details marked as design decisions where applicable

Document map
1. Architectural overview
2. Component responsibilities
3. Data flow and sequence
4. Ledger and cryptographic design
5. Verification architecture
6. Data model and persistence
7. Deployment and runtime model
8. Failure modes and threat model
9. Architecture decisions
10. Evaluation architecture
References

1. Architectural overview
The architecture deliberately separates two guarantees. The Evidence Ledger addresses integrity of the recorded trace. The verifier addresses whether answer claims are supported by that trace. The ledger can be valid while an answer is unsupported; a semantically correct answer can still be untrustworthy if its trace has failed integrity validation.
                 +----------------------+                 | Scenario / Agent     |                 +----------+-----------+                            |                    invoke tool function                            |                 +----------v-----------+                 | Tool Adapter         |                 | capture inputs/result|                 +-----+-----------+----+                       |           |                call tool       append record                       |           |                 +-----v----+ +----v----------------+                 | Tool/API | | Evidence Ledger     |                 +-----+----+ | SQLite + SHA-256    |                       |      +----+----------------+                       +-----------+                                   |                            agent final answer                                   |                        +----------v-----------+                        | Claim Decomposer     |                        +----------+-----------+                                   |                           atomic claims                                   |                        +----------v-----------+                        | Structured Matcher   |                        | direct + derivations |                        +-----+-----------+----+                              |           |                           decided     unresolved                              |           |                              |    +------v---------+                              |    | LLM as Judge   |                              |    +------+---------+                              +-----------+                                          |                               +----------v-----------+                               | Claim-level Report    |                               | verdict + evidence    |                               +-----------------------+
1.1 Architectural style
A modular monolith is recommended: one Python process, separated modules, SQLite persistence and a CLI. The architecture uses a pipeline for verification and an append-only logical sequence for evidence. This minimizes deployment and coordination overhead while preserving clear component boundaries for research.
1.2 Core design principles
Integrity and semantic faithfulness are separate checks.
Record tool results before the final answer is assessed.
Structured evidence matching is the first verification tier; LLM judging is fallback.
Every verdict should be auditable through a method label and evidence pointer.
Evaluation code is separate from the production-like verifier path.
A failed chain check must be visible and cannot be converted into a normal success.
Scope stays CLI-first; no UI or distributed infrastructure in the first research iteration.
2. Component responsibilities
Component
Responsibility
Inputs → outputs
Scenario runner
Loads a test scenario, starts a session and runs the selected agent/tools.
Scenario → session execution.
Agent/tool adapter
Invokes named tools and captures input/output/error consistently.
Tool request → tool result + ledger entry ID.
Tool implementations
Provide controlled outputs from toy APIs, calculator or lookup DB.
Arguments → structured result.
Ledger service
Allocates sequence number, selects prior hash, canonicalizes payload, hashes and persists.
Entry payload → immutable-by-convention stored entry.
Hash verifier
Recomputes hashes and checks chain linkage/order.
Session entries → integrity verdict and first failure.
Claim decomposer
Splits final answer into atomic claims using fixed prompt/schema.
Answer text → claims list.
Structured matcher
Checks direct fields and supported derivations.
Claim + trace → supported/contradicted/unresolved.
LLM judge
Evaluates unresolved claims against relevant evidence.
Claim + evidence → constrained verdict.
Hybrid verifier
Coordinates integrity check, decomposition, matcher, judge and report.
Answer + session → per-claim report.
Baseline runners
Run no-trace and full-trace LLM judges under controlled settings.
Scenario → baseline verdicts.
Metrics/evaluation runner
Compares outputs with gold labels, computes metrics and writes result files.
Gold labels + outputs → metrics and error analysis.
3. Data flow and sequence
3.1 Tool-call sequence
1. Agent -> ToolAdapter: invoke(tool_name, input)2. ToolAdapter -> Tool: execute(input)3. Tool -> ToolAdapter: result OR error/timeout4. ToolAdapter -> Ledger: append(session, input, output/status)5. Ledger: read previous entry hash, assign sequence, canonicalize payload6. Ledger: SHA256(payload bytes), persist entry in SQLite transaction7. Ledger -> ToolAdapter: entry_id + persisted status8. ToolAdapter -> Agent: return tool result to continue task9. Agent -> Verifier: final answer + session_id
3.2 Claim-verification sequence
1. Verifier -> Ledger: verify_chain(session_id)2. If invalid: emit integrity warning; do not silently trust trace.3. Verifier -> Decomposer: final answer4. Decomposer -> Verifier: atomic claims C1..Cn5. For each claim:   a. Matcher searches candidate structured fields.   b. If direct match or declared derivation resolves it, return verdict + pointers.   c. Otherwise send claim + relevant evidence to LLM Judge.   d. Validate verdict schema and referenced entry/field IDs.6. Verifier assembles claim-level report.7. Evaluator compares report with ground truth and logs cost/latency.
3.3 Data sequence example
Suppose a lookup tool returns {count: 42}. The ledger stores that output in entry E2 and links E2 to E1 through previous_hash. The agent writes “The lookup returned 52 records.” The decomposer emits that sentence as one atomic claim. The matcher compares 52 with $.output.count=42 and can mark the claim contradicted/UNSUPPORTED with pointer E2:$.output.count. The report should explain that this is a trace-faithfulness verdict, not a statement about the real-world count.
4. Ledger and cryptographic design
4.1 Linear SHA-256 chain
For each session, entries are ordered by sequence number. The first entry uses a fixed genesis marker; every later entry stores the previous entry's digest. Each entry digest is SHA-256 over the deterministic serialization of the protected entry fields, including previous_hash.
H_0 = "GENESIS_V1"H_i = SHA256(CANONICAL_JSON(        session_id, sequence_no, entry_id, timestamp_utc,        tool_name, input_json, output_json, status, error_info,        schema_version, previous_hash=H_(i-1)      ))
SHA-256 is selected because it is a standard, widely implemented cryptographic hash (NIST FIPS 180-4). It is hard-coded because the research contribution is structured claim faithfulness, not hash agility. The architecture should not imply that SHA-256 alone authenticates who created a record.
4.2 Why canonicalization matters
Hash functions operate on bytes, not abstract JSON objects. Objects that are semantically equivalent but serialized with different key order or whitespace can produce different hashes. Use RFC 8785 JSON Canonicalization Scheme or a rigorously documented deterministic serialization contract. Keep test vectors to avoid cross-version surprises.
4.3 What the chain detects
Modification of a protected field in an entry, when validation recomputes its digest.
Modification of a previous_hash link.
Deletion, insertion or reordering that changes sequence/link expectations.
Truncation, if the verifier compares the observed final chain head against an independently retained expected head/checkpoint.
4.4 What the chain does not guarantee
It does not stop an attacker with write access from rewriting every entry and recomputing all hashes unless a trusted chain head is stored elsewhere.
It does not prove the external tool returned truthful data.
It does not prove the timestamp came from a trusted clock.
It does not provide identity, authorization or non-repudiation by itself.
It does not protect against an entry that was never captured due to a compromised adapter unless the tool invocation path is controlled and tested.
5. Verification architecture
5.1 Two-stage verifier
Stage
Purpose
Decision
Stage 1: atomic claim decomposition
Turn multi-sentence answer into independently testable claims.
Claims list; decomposition failures are logged.
Stage 2A: structured matching
Check exact fields and supported calculations.
SUPPORTED / UNSUPPORTED where clear; otherwise UNRESOLVED.
Stage 2B: LLM judge fallback
Interpret paraphrases or cases not expressible in the fixed matcher.
SUPPORTED / UNSUPPORTED / PARTIALLY_SUPPORTED, with validated pointers where possible.
5.2 Why not one monolithic judge?
Direct number and field checks are naturally deterministic and auditable. A general-purpose judge can misread numeric values or overstate support. The hybrid design reserves the model for semantic cases and can record exactly which rule and field produced a deterministic verdict. This is the central experimental comparison, not a claim that the hybrid system will always outperform a judge.
5.3 Claim types
Type
Example
Handling
Direct numeric
Tool field count=42; claim says count=42.
Structured numeric comparison with type/unit checks.
Derived
Old value=100, new value=120; claim says increased 20%.
Fixed derivation registry; pointer to both operands and formula.
Paraphrased
Tool says status='degraded'; claim says service performance is reduced.
LLM judge with relevant trace; report as a harder semantic case.
5.4 Derived calculation registry
Operation
Formula
Required safeguards
Sum
sum(values)
Explicit operand fields; numeric type validation.
Ratio
numerator / denominator
Reject zero denominator; document units.
Percentage change
(new-old)/old × 100
Reject old=0; explicit rounding/tolerance.
Date delta
end_time - start_time
Normalize timezone; define unit and boundary semantics.
5.5 Verdict/report contract
ClaimVerdict:  claim_id  claim_text  claim_type: direct_numeric | derived | paraphrased | other  verdict: SUPPORTED | UNSUPPORTED | PARTIALLY_SUPPORTED  method: structured_direct | structured_derived | llm_judge  evidence: [{entry_id, field_path}]  rationale  confidence (optional; only if meaning is defined)  processing_error (optional)
Do not use an arbitrary numerical confidence threshold unless it is experimentally specified. A verdict should not cite an entry ID or field path that does not exist.
6. Data model and persistence
6.1 Persistence choice
SQLite is selected for the prototype because it supports transactions, is easy to ship as a local database file and avoids infrastructure overhead. The design is not intended to claim high-throughput concurrent distributed operation.
6.2 Tables
Table
Key fields
Purpose
ledger_entries
session_id, sequence_no, entry_id, previous_hash, entry_hash, payload fields
Evidence record sequence.
sessions (optional)
session_id, created_at, agent/model metadata, chain_head
Session metadata and optional expected head.
evaluation_runs
run_id, timestamp, model IDs, prompt versions, code version, dataset version
Experiment reproducibility.
claim_results
run_id, scenario_id, claim_id, system, verdict, method, evidence pointers, latency, cost
Per-claim output and metrics.
ground_truth
scenario_id, claim_id, gold verdict, claim type, evidence pointers, annotation note
Human-labelled evaluation data.
Keep raw ledger records separate from evaluation outputs. The chain protects the recorded tool-call evidence; evaluation records should still be versioned and backed up, but need not be included in the per-session tool hash chain unless that is an explicit extension.
7. Deployment and runtime model
Developer machine  Python virtual environment  ├── CLI / scenario runner  ├── Python modules (adapter, ledger, verifier, evaluator)  ├── SQLite file (local persistent state)  ├── JSONL scenarios + ground truth  └── results/ (CSV, JSON, logs)       |       +---- outbound HTTPS to chosen LLM provider             (only for decomposition/judge/baselines)
No server deployment is required for the baseline research prototype.
External model calls require a network connection and API credential; deterministic unit tests should not require the provider.
Use environment variables for secrets and redact them from all logs.
Pin dependencies and record code/data versions.
Provide a clean-start command and a small smoke-test scenario in the README.
8. Failure modes and threat model
Failure/threat
Impact
Mitigation / reporting
Tool timeout/error
Missing or misleading trace if silently ignored.
Record status/error entry; return controlled error to agent.
Adapter bypass
A tool call may not be logged.
Centralize invocation through adapter; test capture coverage.
Ledger field mutation
Evidence may be corrupted.
Recompute hashes and verify previous links.
Full-chain rewrite
A recomputed chain may appear internally valid.
Use trusted external chain-head checkpoint if threat model requires it.
Malformed LLM output
Invalid claims/verdicts or parse crash.
Schema validation, bounded retry, controlled failure.
Prompt injection in tool output
Judge may follow malicious content.
Treat trace as quoted untrusted data; fixed system instruction; test attacks.
Incorrect tool result
Wrong real-world answer can still appear supported.
State scope limitation; optionally validate tool sources in future work.
Claim splitting error
Claims may be merged or omitted.
Fixed prompt, decomposition tests, manual gold labels, report error propagation.
Matcher false match
Wrong field/units may support claim incorrectly.
Typed comparison, unit rules, evidence-pointer checks, conservative unresolved state.
Dataset leakage
Held-out performance overestimated.
Freeze held-out domain before tuning and document any exposure.
8.1 Threat model statement
The initial threat model covers accidental or deliberate post-write modification of the stored ledger, plus verifier errors caused by malformed outputs or untrusted tool content. It does not claim resistance to a fully compromised host, compromised Python runtime, malicious database administrator who can rewrite all records and checkpoints, or dishonest external tools. Stronger adversarial guarantees require independent anchoring, access controls and deployment-specific security design.
9. Architecture decisions
Decision
Choice
Alternatives intentionally deferred
Architecture style
Modular monolith / CLI
Microservices and distributed orchestration.
Ledger storage
SQLite
MongoDB/cloud DB for initial prototype.
Hash algorithm
Hard-coded SHA-256
Configurable algorithms or custom cryptography.
Chain
Linear previous-hash chain
Blockchain/Merkle tree.
Claim strategy
Structured-first + LLM fallback
Single all-purpose LLM judge only.
Interface
CLI
Streamlit/React dashboard.
Evaluation
Three systems on same labelled scenarios
Uncontrolled demonstrations or no-trace-only comparison.
Dataset scope
40–60 scenarios + held-out domain
Large-scale benchmark claim without resources.
10. Evaluation architecture
Frozen scenario dataset       |       +--> Baseline A: LLM judge (no trace)       |       +--> Baseline B: LLM judge (full trace)       |       +--> Hybrid: ledger validation -> decomposer                    -> structured matcher -> judge fallback       |       vPer-claim result records       |       +--> precision / recall / F1       +--> localization accuracy       +--> false-positive rate       +--> direct / derived / paraphrased breakdown       +--> latency and estimated cost       +--> tamper-detection rate       +--> held-out domain and failure analysis
Run all systems on the same labelled claims. Keep prompts and model identifiers as comparable as possible, especially between Baseline B and the hybrid judge fallback. Explain any unavoidable differences. A single small dataset supports a scoped feasibility result, not a universal conclusion.
References and research notes
Liu, X. et al. (2026). AgentHallu: Benchmarking Automated Hallucination Attribution of LLM-based Agents. EMNLP 2026. https://aclanthology.org/2026.emnlp-main.925/
NIST. Secure Hash Standard, FIPS PUB 180-4. https://csrc.nist.gov/pubs/fips/180-4/upd1/final
NIST CSRC. Hash Functions overview. https://csrc.nist.gov/projects/hash-functions
RFC 8785 (2020). JSON Canonicalization Scheme (JCS). https://www.rfc-editor.org/rfc/rfc8785.html
OWASP GenAI Security Project. OWASP Top 10 for LLM Applications 2026. https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/
Project source materials: user-provided project proposal, and uploaded Roadmap.pdf (scanned PDF; roadmap text extracted using OCR).
Evidence and interpretation note: AgentHallu's published numbers are background motivation only. They must not be presented as results from this project. The proposal's novelty statement is a project hypothesis to investigate, not an established universal claim. A literature review should confirm the final related-work and novelty wording before publication.