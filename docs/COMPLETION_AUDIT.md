# Report implementation audit - 16 October 2026

Scope: implement the existing single-account FABC design in the submitted case study,
verify the existing banking system, and record measured results. No new novelty,
multi-hop attribution, incremental caching, GNN or patent investigation was added.
The submitted proposal remains a historical document; this file records later work.

## What was missing and is now implemented

| Report requirement | Implementation and verification |
| --- | --- |
| Ordered account ledger | `Account.ledger_seq`, two ledger entries per service transfer, globally ordered account locks, monotonic server-recorded UTC timestamps. Caller timestamps cannot change evidence ordering. |
| Schema migration and retention | Additive migrations `0003`, `0004`; composite evidence/target foreign keys, unique transfer sides and certificate, numeric bounds checks, indexed history and review queries. Evidence updates/deletes are rejected by database triggers. Certified transaction monetary facts cannot be edited. |
| Exact funding interval | `app/services/flow_bounds.py`; Decimal arithmetic; both report examples and exhaustive feasible integer allocations checked. |
| Window, opening anchor and continuity | Ten-minute inclusive start, source sequence prefix, opening snapshot, arithmetic/sequence checks. Credits outside the window become opening funds. |
| Missing evidence and scan cap | `INCOMPLETE`, a reason, NULL bounds and no review flag. Maximum 10,000 history entries; no exact claim from a truncated prefix. |
| Existing accounts | Migration marks the observation start. Windows overlapping unobserved legacy history are incomplete. Historical transfers are preserved, without fabricated certificates. |
| Atomic transfer integration | Balance changes, ledger pair, certificate, ordered membership, ordinary inference, prediction, alerts and audit writes share one transaction. An injected failure after certificate writes rolls everything back. |
| Idempotency | Optional globally unique request key; retries return the committed transaction, a different payload gets 409. Customer locking serializes matching retries. Decimal amount formatting is canonical. |
| Persisted evidence and replay | Versioned canonical JSON, fixed two-decimal amounts, UTC timestamps, SHA-256; replay checks stored membership, live ledger facts, certificate identity, bounds, versions and results. Digest is not protection against an administrator rewriting the database. |
| Analyst interface | Banking transaction certificate inspection, replay button and separate funding-review queue. The fixed policy is 80% minimum recent funding plus three distinct incoming accounts. ML probability remains separate. |
| Relational reporting | `flow_certificate_detail_view` joins certificates, ordered evidence and ledger entries. |
| DBMS demonstrations | Rollback and simultaneous debit demos also check ledger/certificate counts. Isolated demo histories are retained for replay. |
| Detection comparisons | Seeded synthetic fitted ML, ML plus behaviour, FIFO, LIFO, haircut, velocity, lower-bound, upper-bound and no-counterparty comparisons. Designed benign counterexamples remain possible; the policy does not prove fraud. |
| Database cost | Disposable SQLite benchmark with real fitted Random Forest inference, certificates on/off, p50/p95/p99, sequential throughput, evidence rows/JSON bytes, indexed plan and replay agreement. |
| Historical graph evaluation | Separate label-free graph implementation emits features before updating each hourly step. A chronological PaySim RF comparison selects the threshold only on validation; original model artifacts are preserved. |
| Missing documented command | Added `scripts/run_full_pipeline.py` to orchestrate the existing offline scripts. Full-data training remains an explicit command and does not overwrite models during this audit. |

## Operating instructions

```bash
source .venv/bin/activate
export PYTHONPATH=src:.
alembic upgrade head
python -m pytest -q
python scripts/evaluate_flow.py
python scripts/benchmark_flow_database.py
python scripts/evaluate_historical_graph.py
uvicorn app.main:app --reload
# In a second terminal with the same environment:
streamlit run app/streamlit_app.py
```

The existing local SQLite database was backed up to
`data/banking_before_flow_0003.db`, then upgraded through `0004`.
No existing transaction was deleted or retrospectively attributed.

API additions:

- `GET /transactions/{id}/flow-certificate`
- `GET /transactions/{id}/flow-certificate/replay`
- `GET /fraud/flow-reviews`
- Optional `idempotency_key` on `POST /transactions`

For transfers predating migration, certificate inspection returns 404. New transfers
from migrated accounts can be INCOMPLETE until a full window has been observed.
Newly opened accounts have a known opening balance. Initial deposits are treated
as opening funds; arbitrary direct balance mutations are outside the protocol.
Reversals must be new opposite-direction transfers; retained movements are never edited.

## Validation and limitations

The executable checks cover examples, exhaustive bounds, inclusive time boundaries,
opening anchors, migration epochs, cap handling, balance gaps, immutable evidence,
API replay, retry conflicts, atomic failure, simultaneous debits and Streamlit banking.
Generated evaluation reports are copied to `docs/evaluation/` for review.

PostgreSQL-specific verification remains **unverified in this run**. Docker's daemon
is unavailable and both the top-level and nested Docker Desktop application fail to
launch with `kLSNoExecutableErr`. No working local PostgreSQL server binary was found.
The existing test fixture supports a disposable PostgreSQL schema when
`TEST_DATABASE_URL` is provided:

```bash
TEST_DATABASE_URL="$DATABASE_URL" python -m pytest tests/test_banking.py tests/test_flow_evidence.py -q
```

Accordingly, PostgreSQL row-lock behavior, these new PostgreSQL trigger definitions,
lock-wait timings, concurrent throughput and restart recovery cannot be claimed
verified here. SQLite persistence is exercised across committed sessions and a recreated engine/connection pool; this is
not a substitute for a database-server restart test.

The history scan and two-entry conservation contract rely on all movement writers
using the transfer service and taking account locks. Use a dedicated runtime DB
role, restrict direct monetary writes, and retain backups. This local course app
still has no authentication. Owners/administrators can bypass object protections.

The original full-graph experiment remains available and can include future data;
use the separate historical experiment for a defensible temporal comparison.
Sampled PaySim is not real-bank validation and its hourly steps cannot establish
FABC's ten-minute detection quality. The synthetic scenario study fixes the report's
policy without tuning; its labels are generated scenario labels. Full matched-bank
validation, comprehensive window/threshold sweeps and production deployment are
research/operational follow-ups, not measured successes from this implementation.

## Measured results from this run

- Full suite: **122 passed, 1 skipped**; the skip requires PostgreSQL. The starting suite had 107 passes and the same skip. Ruff and `git diff --check` pass for this work.
- The scenario study contains 1,200 seeded targets, including low-opening-balance benign collections matched to pass-through-like histories. FABC precision is 39.25%, recall 42.00%, with 130 false alerts per 1,000 benign targets at the fixed report policy. Haircut has higher recall and average precision in this particular construction. These results expose ambiguity rather than establish superiority.
- The fitted ML plus behaviour comparison uses synthetic target balance snapshots and explicit single-customer history assumptions. It is a domain-mismatch stress test, not a retrained fraud benchmark. No future or target labels are supplied as model inputs.
- The chronological PaySim experiment sampled 127,171 naturally imbalanced rows. Training: 117,936 rows / 91 fraud; validation: 5,401 / 34; test: 3,834 / 38. Validation begins at step 404 and test at step 564. Transaction RF detected all 38 sampled test frauds; historical graph RF detected 36, with no false positives for either at their validation-selected thresholds. These small sampled results do not establish generalisation or a graph improvement.
- In the final sequential SQLite run with a warm fitted model, certificate transfer p50/p95/p99 was 20.20/22.01/22.46 ms; the control was 17.11/18.29/18.53 ms. All 100 persisted certificates replayed. The query plan used `idx_ledger_account_recorded_seq`. Timing varies by machine/load; the control disables both ledger and certificate writes, so this is their combined overhead.

Saved result snapshots:

- [Synthetic comparison](evaluation/flow_evaluation.json)
- [Database overhead and indexed plan](evaluation/flow_database_benchmark.json)
- [Chronological graph comparison](evaluation/historical_graph_evaluation.json)

The optional multi-account extension, incremental expiry algorithm and patent/novelty investigation remain deferred as requested. PostgreSQL execution and broader research sweeps remain explicitly outstanding; this audit does not certify the entire report as experimentally complete.
