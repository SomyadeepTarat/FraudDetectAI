# Joint funding research prototype

An offline implementation of the narrow research candidate described in the [disclosure draft](INVENTION_DISCLOSURE_B_DRAFT.md). Patent novelty and inventive step remain unresolved. The current synthetic experiment does not establish superiority over a simple reachability baseline. This module is not connected to live transfers or automatic fraud decisions.

## Run

Use the existing project environment (NetworkX is already in requirements.txt). From the repository root:

```bash
.venv/bin/python -m pytest tests/test_joint_funding.py -q
.venv/bin/python -m scripts.evaluate_joint_funding
.venv/bin/python -m scripts.run_joint_funding \
  docs/evaluation/joint_funding_example.json \
  docs/evaluation/joint_funding_certificate.json
```

The evaluator regenerates measured timings, a synthetic example and its benchmark report. The CLI writes a standalone certificate and evidence-selection recommendation. No credentials, customer dataset, database migration or trained model are required.

## Implemented

- Exact integer min/max source-cohort holdings across selected final accounts, through chronological internal transfers and external credits.
- Endpoint witnesses with a separate conservation/capacity/negative-residual-cycle optimality verifier.
- Decision-directed query ranking using exhaustive outcome partitions and worst-case unresolved-width reduction per cost.
- Applying a chosen evidence outcome to a copy of the input and fully recomputing bounds.
- Independent exhaustive-allocation oracle and reproducible controlled query comparisons.

## Input contract

See the generated example JSON for the complete schema. Top-level keys are `ledger`, `threshold` and `queries`. All money and thresholds are integer minor units (INR paise in the examples). Costs are positive integer acquisition-cost units, not necessarily monetary values.

`ledger` contains `snapshot_id`, `cohort_id`, `currency`, `complete`, `opening`, `movements`, and `targets`. Every opening account requires an evidence ID, account ID, balance `amount`, and independently supported `lower`/`upper` cohort-attribution bounds. Internal movements require unique ID, known source and destination accounts, and a positive amount. An external credit uses `source: null` and requires boundary attribution bounds. The supplied movement order is authoritative; timestamps are not inferred or sorted.

Targets are distinct accounts' balances at the final snapshot, not arbitrary transfers or sums of serial payments. A transfer is not a new source injection. Cohort bounds at independent boundaries must not double-count the same injection. External withdrawals/re-entry, missing balances, foreign exchange, fees, overdrafts and overlapping source cohorts are outside scope. Missing chronology or movements must not be represented as `complete: true`.

A query identifies a boundary record, an evidence reference, a positive cost, and sorted inclusive integer outcome intervals that partition the current boundary interval without gaps or overlaps. An evidence reference must correspond to a record the caller could actually obtain and authenticate. It is not permission to query a private institution. Internal allocation choices cannot be queried as though fungible funds have an observable unique identity.

## Output contract

`certificate.result` contains `lower`, `upper`, and a funding `condition`: MET, NOT_MET or UNRESOLVED relative to the supplied threshold. None is a fraud probability, legal determination or freeze instruction.

`verify(certificate)` checks its digest, rebuilds the network, and verifies endpoint feasibility and optimality without rerunning the optimizer. It does not authenticate source data; a rewritten ledger with a recomputed digest requires an external trusted snapshot to detect. Software version and snapshot metadata are recorded for replay.

`evidence_selection` contains the selected query ID (or null), the policy version, the base certificate digest, and every query's outcome intervals, guaranteed ambiguity reduction and rational benefit/cost score. Selection is deterministic and greedy. It is not a globally optimal multi-query plan; zero one-step benefit may hide useful query combinations. There is no learned response distribution, bank connector or incremental solver cache.

## Validation and interpretation

The recorded run passed 272 new tests, including 250 seeded ledgers matched against exhaustive integer allocations. The full suite passed 394 tests with one skip. PostgreSQL validation is not established by that local run.

In 100 deliberately simple query cases, the proposed policy and a reachability-filter baseline both resolved 100 cases for every possible selected-query response. A widest-boundary baseline resolved zero and seeded random selection resolved 40. The fair conclusion is that the mechanism works on this controlled family; it has not demonstrated a new advantage over stronger methods or fraud-detection accuracy on real data.

The original research note included incremental certificate maintenance, learned query value, and richer missing-record requests. Those remain future research, not capabilities of this prototype. A stronger next experiment must include connected but capacity-limited paths, query complementarity, mixed legitimate businesses, realistic evidence costs, and withheld query families. Patent assessment must consider the known constituent techniques and their combination.

## Disclosure artifacts

- `docs/INVENTION_DISCLOSURE_B_DRAFT.md`: editable answers to all ten questions.
- `output/pdf/FraudDetectAI_Invention_Disclosure_B_Draft.pdf`: supplied template filled as a static copy, with a technical annex and provisional TRL 3 selection.
- `scripts/create_invention_disclosure.py`: reproducible PDF/Markdown authoring script; requires the bundled PDF runtime (`reportlab`, `pypdf`) and the original template at the configured path. Measurements are read from the saved evaluation JSON. Test counts describe the recorded validation run and must be updated if tests change.

The source form and existing application code were preserved. No patent filing, production integration or external submission was performed.
