Tool Call Evidence Ledger
A Framework for Verifiable, Tamper-Evident Tool Use in Agentic Systems
Developer Guide and Implementation SpecificationVersion 1.0 | 28 October 2026 | Research prototype specification
Document
Developer Guide and Implementation Specification
Project type
Research prototype / experimental evaluation
Primary guarantee
Traceability of claims to recorded tool outputs + tamper evidence
Status
Baseline specification; implementation details marked as design decisions where applicable

Document map
1. Implementation principles
2. Recommended repository structure
3. Environment and setup
4. Ledger implementation contract
5. Hash-chain algorithm
6. Claim verification pipeline
7. CLI/API contracts
8. Testing strategy
9. Experiments and reproducibility
10. Security, debugging and troubleshooting
11. Eight-week build plan
References

1. Implementation principles
This guide translates the project proposal and roadmap into an implementable Python research prototype. The most important separation is between (a) integrity of the stored trace and (b) faithfulness of claims to that trace. Passing one check must never imply the other passed.
Keep the hash algorithm fixed: SHA-256.
Use a linear previous-hash chain; do not introduce blockchain, Merkle trees or algorithm plug-ins for this scope.
Write every tool result before the final answer is verified.
Use structured matching first; call the LLM judge only when the structured matcher cannot decide.
Treat tool outputs and LLM outputs as untrusted input.
Log evaluation records at run time; do not reconstruct metrics from memory at the end.
2. Recommended repository structure
tool-call-evidence-ledger/  README.md  pyproject.toml                 # or requirements.txt  .env.example                   # variable names only; never commit real keys  src/evidence_ledger/    __init__.py    config.py    models.py                    # typed schemas / enums    canonicalize.py              # deterministic JSON bytes    ledger.py                    # SQLite persistence + append + verify    hashing.py                   # fixed SHA-256 helper    tools/      __init__.py      adapter.py                 # invoke tool and capture result/error      calculator.py      lookup_db.py      fake_weather.py    claims/      decomposer.py      taxonomy.py      structured_matcher.py      derivations.py      llm_judge.py      verifier.py    evaluation/      dataset.py      baselines.py      metrics.py      runner.py      reports.py    cli.py  tests/    test_hashing.py    test_ledger.py    test_tamper_detection.py    test_matcher.py    test_verifier.py    test_evaluation.py  data/    scenarios.jsonl    ground_truth.jsonl    annotation_guidelines.md  results/    .gitkeep  docs/    SRS.md    architecture.md    developer_guide.md
The structure is a recommendation, not an assertion that this repository already exists. Keep implementation simple: do not add a web server or frontend unless the scope is formally changed.
3. Environment and setup
Install a supported Python version (recommend Python 3.11 or newer, pinned in project metadata).
Create a virtual environment: python -m venv .venv; activate it for the current shell.
Install dependencies from the pinned requirements/pyproject file.
Copy .env.example to .env and add the chosen model provider key locally. Never commit .env.
Initialize the SQLite database through the documented CLI command or startup migration.
Run unit tests before running any experiment.
Run one toy scenario and verify the chain before enabling LLM calls.
Dependency policy: prefer Python standard-library sqlite3, hashlib, json, datetime, uuid, logging, argparse/typer and unittest/pytest. Add a model SDK only for the selected provider. Pin dependency versions and record the model identifier, because model aliases can change.
4. Ledger implementation contract
4.1 Record schema
LedgerEntry:  session_id: str  sequence_no: int  entry_id: str  timestamp_utc: str  tool_name: str  input_json: JSON-compatible value  output_json: JSON-compatible value | null  status: "success" | "error" | "timeout"  error_info: object | null  schema_version: int  previous_hash: str  entry_hash: str
4.2 SQLite tables (suggested)
CREATE TABLE IF NOT EXISTS ledger_entries (  session_id TEXT NOT NULL,  sequence_no INTEGER NOT NULL,  entry_id TEXT NOT NULL UNIQUE,  timestamp_utc TEXT NOT NULL,  tool_name TEXT NOT NULL,  input_json TEXT NOT NULL,  output_json TEXT,  status TEXT NOT NULL,  error_info TEXT,  schema_version INTEGER NOT NULL,  previous_hash TEXT NOT NULL,  entry_hash TEXT NOT NULL,  PRIMARY KEY (session_id, sequence_no));CREATE INDEX IF NOT EXISTS idx_ledger_session  ON ledger_entries(session_id, sequence_no);
Use a database transaction for insertion. Determine the previous hash and next sequence within the same transaction so concurrent writers cannot accidentally fork a session chain. For the initial single-process prototype, a simple write lock/transaction is sufficient; document that distributed multi-writer operation is not a goal.
5. Hash-chain algorithm
5.1 Protected payload
The entry hash covers all fields whose alteration should be detected, including previous_hash. Exclude entry_hash itself to avoid a self-reference. Canonicalize the protected payload to a deterministic UTF-8 byte sequence before hashing. RFC 8785 defines one JSON canonicalization approach; a simpler custom serializer is acceptable only if it is precisely specified and tested across the project.
payload = {  "session_id": session_id,  "sequence_no": sequence_no,  "entry_id": entry_id,  "timestamp_utc": timestamp_utc,  "tool_name": tool_name,  "input_json": input_value,  "output_json": output_value,  "status": status,  "error_info": error_info,  "schema_version": schema_version,  "previous_hash": previous_hash}entry_hash = sha256(canonical_json(payload).encode("utf-8")).hexdigest()
Genesis rule: define one fixed genesis marker such as the literal string GENESIS_V1 as the previous_hash for sequence 1. Do not treat an arbitrary empty string as interchangeable across implementations.
5.2 Pseudocode
append(session, call_record):    begin database transaction    last = latest entry for session, if any    sequence = 1 if no last else last.sequence_no + 1    previous = GENESIS_V1 if no last else last.entry_hash    payload = build_protected_payload(call_record, sequence, previous)    digest = SHA256(canonical_json(payload).UTF8)    insert payload + digest    commit    return entry_id, digestverify(session):    entries = load session entries ordered by sequence_no    expected_previous = GENESIS_V1    expected_sequence = 1    for entry in entries:        if entry.sequence_no != expected_sequence: return INVALID("sequence gap/order")        if entry.previous_hash != expected_previous: return INVALID("previous hash mismatch")        recomputed = SHA256(canonical_json(entry.without_entry_hash).UTF8)        if recomputed != entry.entry_hash: return INVALID("entry hash mismatch")        expected_previous = entry.entry_hash        expected_sequence += 1    compare final expected chain head to independently stored checkpoint, if configured    return VALID
5.3 Security boundary
A linear hash chain detects changes relative to a trusted expected chain. If an attacker can edit every record and recompute the complete chain, internal validation alone cannot distinguish the rewritten ledger from a newly created valid one. For this research prototype, document the threat model clearly. If stronger protection is later required, preserve the final chain head in a separate trusted location, sign it, or use append-only external storage; these are future extensions, not part of the core prototype.
5.4 Canonicalization rules
Use UTF-8 bytes and a deterministic object-key ordering/number/string serialization rule.
Reject unsupported values such as NaN/Infinity if the chosen JSON contract disallows them.
Preserve array order; do not sort arrays.
Normalize timestamps to one explicit UTC ISO-8601 format before hashing.
Never hash a human-formatted pretty-print if the same object can be serialized differently elsewhere.
Write test vectors for nested objects, Unicode, nulls, numbers, arrays and empty fields.
6. Claim verification pipeline
6.1 Decomposition
Input is the final answer. The decomposer returns an ordered list of atomic claims with stable IDs and the original claim text. Require structured JSON output and validate required keys, types, and count. If output is malformed, retry under a bounded policy or return a controlled decomposition error; never parse arbitrary model prose as if it were trusted structured data.
6.2 Structured matching
Rule
Suggested implementation
Caution
Direct numeric
Parse numeric literals and compare to typed numeric fields; track units and tolerance explicitly.
42, 42.0 and '42%' are not automatically equivalent; units matter.
Entity/value
Compare normalized entity/value strings to candidate fields while retaining exact original value.
Normalization must not erase meaningful distinctions.
Sum
Add declared numeric fields and compare to claim value.
Record all operand pointers and arithmetic expression.
Ratio
Divide explicitly selected numerator/denominator fields.
Handle zero denominator and units.
Percentage change
(new - old) / old * 100, when old is nonzero.
Define sign convention and rounding tolerance.
Date delta
Compute difference between declared date/time fields.
Timezone and inclusive/exclusive semantics must be documented.
Return one of: MATCH_SUPPORTED, MATCH_CONTRADICTED, UNRESOLVED. Do not label a claim unsupported merely because a naive string search failed; absence of a direct match can mean the claim is paraphrased or derived. The matcher should be conservative and route unresolved cases to the judge.
6.3 LLM judge fallback
Provide one claim, relevant ledger entries and explicit output schema.
Instruct the judge to assess only support in the supplied trace, not real-world truth.
Treat instructions embedded in tool output as untrusted evidence text; they must not override the judge's verification instructions.
Require verdict SUPPORTED / UNSUPPORTED / PARTIALLY_SUPPORTED and evidence pointers when present.
Validate that returned entry IDs and field paths actually exist.
Log model ID, prompt version, latency, token/cost estimate and parse errors.
6.4 Verdict semantics
Verdict
Meaning
Example
SUPPORTED
All material parts of the claim are supported by one or more recorded fields or valid declared derivation.
Trace count=42; claim says count is 42.
UNSUPPORTED
The trace does not support the claim, or the trace contradicts a material assertion.
Trace count=42; claim says count is 52.
PARTIALLY_SUPPORTED
Some parts are supported but at least one material component is missing or contradicted.
Trace says 42 results; claim says 42 results were verified as safe, but safety was not measured.
6.5 Answer-level policy
Keep claim-level verdicts primary. An aggregate answer status may be reported as a summary, but define its rule explicitly (for example, any unsupported claim prevents a fully-supported status). If the ledger chain is invalid, flag integrity failure prominently and do not silently treat the recorded entries as trusted evidence.
7. CLI contract
Command (suggested)
Purpose
ledger init
Create or migrate the local SQLite database.
ledger run --scenario ID
Execute a scenario and capture tool calls.
ledger inspect --session SESSION_ID
Print entries and their IDs/fields.
ledger verify --session SESSION_ID
Validate sequence and hash chain.
verify answer --session SESSION_ID --input answer.txt
Run decomposition and claim verification.
evaluate --dataset data/scenarios.jsonl
Run Baseline A, Baseline B and hybrid systems.
evaluate report --run RUN_ID
Export metrics and per-claim records to CSV/JSON.
Exact CLI framework and syntax can be chosen during implementation. These are proposed commands, not claims that a CLI already exists.
8. Testing strategy
Test group
Cases
Expected outcome
Hash unit tests
Same input twice; changed payload; changed previous hash.
Same input gives same digest; mutations change digest.
Ledger tests
Append 1–3 records; inspect order; failed tool; empty session.
Correct sequence, persisted errors and clear empty-session result.
Tamper tests
Edit output, delete entry, reorder rows, modify previous_hash, alter sequence.
Chain verification fails with first useful diagnostic.
Canonicalization tests
Nested JSON, Unicode, arrays, decimals, nulls, unsupported values.
Stable deterministic bytes or explicit rejection.
Matcher tests
Exact numeric, unit mismatch, absent value, wrong value, sum, ratio, percentage change, date delta.
Correct match/contradiction/unresolved result and evidence pointers.
Judge tests
Supported paraphrase, unsupported claim, partial claim, malformed JSON, prompt injection in tool output.
Validated verdict; untrusted output does not change instructions.
End-to-end
Clean scenario and injected misreport/invention/misattribution.
Ledger, verifier and evaluator outputs are complete and traceable.
9. Experiments and reproducibility
Create 40–60 realistic scenarios across one primary toy domain, mixing clean and deliberately corrupted final answers.
Hand-label each atomic claim as supported, unsupported or partial and annotate the exact evidence field where possible.
Write an annotation guide; record ambiguous cases rather than silently forcing labels.
Reserve a small, structurally different second domain as held-out data before tuning matcher rules.
Run Baseline A, Baseline B and hybrid verifier on the same scenarios and freeze the model/prompt configuration where possible.
Export per-claim verdicts, ground truth, localization, latency, cost and error information to CSV/JSON.
Report precision, recall, F1, false-positive rate, localization accuracy, claim-type breakdown, generalization and tamper detection.
Review 15–20 failures if feasible and classify them (decomposition error, wrong field, calculation rule, judge false positive/negative, missing evidence, serialization/ledger issue).
9.1 Ground-truth record
{  "scenario_id": "S-014",  "claim_id": "C2",  "claim_text": "The value increased by 20%.",  "gold_verdict": "SUPPORTED",  "claim_type": "derived",  "evidence": [    {"entry_id": "S-014:1", "field_path": "$.output.old_value"},    {"entry_id": "S-014:2", "field_path": "$.output.new_value"}  ],  "derivation": "(new_value - old_value) / old_value * 100",  "annotator_note": "The arithmetic and rounding rule are stated."}
10. Security, debugging and troubleshooting
API key appears in logs: fix redaction before the record is persisted; rotate the key if exposed.
Valid entries report hash mismatch: compare the exact canonical bytes, timestamp normalization, schema version and previous_hash used at append time.
False unsupported verdict on paraphrase: ensure unresolved claims go to the judge rather than being rejected by failed string matching.
False supported verdict on number: inspect units, rounding tolerance, claim decomposition and evidence pointer validation.
Judge follows malicious instructions in tool output: strengthen separation between instruction and quoted evidence; test indirect prompt-injection cases.
Evaluation scores change unexpectedly: freeze scenario files, model ID, prompt versions and thresholds; record all run metadata.
A corrupted chain appears valid after full rewrite: expected if no trusted checkpoint exists; explain the threat-model boundary and consider external anchoring as future work.
11. Eight-week build plan
Week
Work
Deliverable
1
Literature review and hypothesis lock; read 10–12 relevant papers and record each paper's scope/gap.
Literature-review notes; hypothesis; Baselines A/B fixed.
2
Schema, claim taxonomy, verifier stages and architecture diagram.
Schema, taxonomy and architecture specification.
3
Build tool adapters, SQLite ledger, SHA-256 chain and tamper tests; CLI only.
Ledger module and passing tamper test.
4
Implement decomposition, direct/derived matcher, judge fallback and baselines.
Decomposer, matcher, judge baseline and hybrid verifier.
5
Build and label 40–60 scenarios; reserve second domain.
Scenarios, ground truth and annotation guidelines.
6
Run experiments, calculate metrics and categorize failure cases.
CSV results, generalization results and error analysis.
7
Write paper in Methods → Results → Related Work → Introduction → Abstract order.
4–6 page workshop/student-paper draft and limitations.
8
Clean repository, verify README, diagram, rerun tests and prepare pitch.
Reproducible repo, final paper and 60-second pitch.
References and research notes
Liu, X. et al. (2026). AgentHallu: Benchmarking Automated Hallucination Attribution of LLM-based Agents. EMNLP 2026. https://aclanthology.org/2026.emnlp-main.925/
NIST. Secure Hash Standard, FIPS PUB 180-4. https://csrc.nist.gov/pubs/fips/180-4/upd1/final
NIST CSRC. Hash Functions overview. https://csrc.nist.gov/projects/hash-functions
RFC 8785 (2020). JSON Canonicalization Scheme (JCS). https://www.rfc-editor.org/rfc/rfc8785.html
OWASP GenAI Security Project. OWASP Top 10 for LLM Applications 2026. https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/
Project source materials: user-provided project proposal, and uploaded Roadmap.pdf (scanned PDF; roadmap text extracted using OCR).
Evidence and interpretation note: AgentHallu's published numbers are background motivation only. They must not be presented as results from this project. The proposal's novelty statement is a project hypothesis to investigate, not an established universal claim. A literature review should confirm the final related-work and novelty wording before publication.