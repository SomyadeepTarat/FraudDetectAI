# Invention Disclosure Format B - research draft

18 October 2026. Answers mapped to all ten questions. Patent novelty remains unresolved.

## 1. Title of the invention

Decision-Directed Ledger Evidence Acquisition Using Joint Funding Bounds. Working title for a research disclosure, not a representation that a patent has been granted or that novelty is established.

## 2. Field / area of invention

Computer-implemented financial investigation, transaction-network analysis, constrained optimization, and evidence selection. Intended application: investigation of complaint-linked instant-payment proceeds that split through mule accounts, mix with other funds, and converge at related recipients.

## 3. Prior patents and publications from literature

| Prior art | Overlap | Difference / limitation |
| --- | --- | --- |
| [P1: FlowScope (AAAI, 2020)](https://cdn.aaai.org/ojs/5906/5906-13-9131-1-10-20200513.pdf) | Multi-step flow-based laundering detection. | Flow conservation and multi-account tracing are not new. |
| [P2: US11854091B1 (2023); priority 2020-07-24](https://patents.google.com/patent/US11854091B1/en) | Transaction tracing; FIFO attribution and graph transformations. Claim 1 addresses policy enforcement with distributed mapping. | Our prototype retains all feasible allocations instead of choosing FIFO. Tracing and replay remain overlapping concepts. |
| [P3: CN112465638A (2021)](https://patents.google.com/patent/CN112465638A/en) | Split/combined transaction tracing using graph storage, parameters and search. | Split-and-merge tracking alone is not a novelty claim. |
| [P4: US20250045762A1 (2025)](https://patents.google.com/patent/US20250045762A1/en) | Claim 1 covers temporal graph profiles updated using new transactions. | Generic graph features and temporal updates are established. |
| [P5: WO2026125967A1 (2026)](https://patents.google.com/patent/WO2026125967A1/en) | Claim 1 includes ML-based fraud identification, fund tags, tracing and responsive measures. | Our offline prototype computes intervals and recommends evidence; tracking plus action is already disclosed. |
| [P6: EDDI (2018 preprint)](https://arxiv.org/abs/1809.11142) | Dynamic acquisition of useful missing information using expected information gain. | Selecting the next evidence is not new in general; the proposed policy uses worst-case funding-condition ambiguity. |
| [P7: CN120852050B (2026); A publication 2025-10-28](https://patents.google.com/patent/CN120852050B/en) | Graph fusion, fund-path reconstruction and counterfactual causal-query scenarios. | Counterfactual fund-path analysis is overlapping prior art; our queries concern obtainable boundary evidence. |

Preliminary public-source review on 18 October 2026. Publication identifiers are not legal-status opinions. No exhaustive family or prosecution review.

## 4. Summary and background: gap and novelty

A mixed account does not identify which incoming rupees funded an outgoing payment. Independent per-payment intervals can also conceal a collective constraint: two payments may each have zero minimum source attribution although their combined minimum is positive. The existing project implements single-account FABC; this prototype computes joint terminal-account holdings across a chronological network.

The proposed gap is decision-directed evidence acquisition tied to joint feasible funding bounds: when a funding condition is unresolved, choose an obtainable boundary record using its worst-case effect on that condition. Existing work establishes flow tracing, graph detection and active information acquisition separately. The combination remains an inventive-step hypothesis. No claim-level novelty clearance or freedom-to-operate conclusion has been obtained.

Assessment: sufficient motivation for an isolated experimental prototype; insufficient evidence to assert patentability or improved real-world fraud detection. The simple reachability baseline ties the proposed selector in the current microbenchmark. Accordingly, readiness for production implementation or filing-ready novelty claims has not been established.

## 5. Objectives of invention

Compute exact minimum and maximum cohort-attributable funds across a set of final account holdings without double counting serial transfers.

Distinguish a met, unmet or unresolved funding review condition from any fraud verdict; preserve irreducible uncertainty caused by fungibility.

Select a positive-benefit, obtainable evidence query under an explicit acquisition cost and exhaustive response partitions, without inventing response probabilities.

Produce a replayable evidence-bound certificate and independently check endpoint feasibility and optimality. Measure correctness and query behavior before introducing a production workflow.

## 6. Working principle in brief

Build an account-event network from a complete ordered ledger. Capacity-constrained edges represent transfers and retained balances. Boundary intervals describe independently supported source-cohort amounts. Solve two integer min-cost circulations to find the smallest and largest total cohort amount in selected final accounts.

If the interval straddles the review threshold, simulate every supplied outcome of each obtainable boundary-evidence query. Rank queries by guaranteed reduction in unresolved interval width per unit cost. Apply an authenticated response as a constraint update, fully recompute the certificate, and keep the response reference. The prototype simulates acquisition; it does not contact banks.

## 7. Detailed description and drawing

Inputs: snapshot identifier, cohort identifier, one currency, opening balances with cohort bounds, an ordered list of internal transfers or external credits, distinct target accounts, a positive review threshold, and optional query specifications. Values are integer minor units. No overdrafts, external withdrawals, fees, FX or incomplete ledgers are supported. A complete=true declaration is a caller assertion, not independently authenticated bank evidence.

Network: each balance event receives a new node. A transfer edge has the posted transfer capacity; a carry edge has the balance retained after the event. Opening funds and external credits enter through boundary edges with lower/upper cohort amounts. Every final account drains to a common sink; a return edge closes the circulation. Only selected final-account sink edges enter the objective. This terminal frontier prevents serial double counting.

Let F be all integer flows satisfying edge bounds and conservation, and T be target terminal edges. Compute L = min over z in F of sum(z_e for e in T), and U = max over z in F of the same sum. The implementation uses NetworkX network_simplex with lower-bound demand transformation and opposite objective signs. These are established optimization techniques, not claimed inventions.

For threshold tau: MET if L >= tau; NOT_MET if U < tau; otherwise UNRESOLVED. These refer exclusively to source funding. Complaint-linked sources can be mistaken, legitimate merchants can pass funds through, and exact attribution cannot prove deceptive intent.

Define D([L,U]) = U-L for an unresolved condition and zero otherwise. A query q has positive integer cost c_q and outcomes that partition the entire current boundary interval with no gaps or overlaps. Score(q) = (D(current) - max over outcomes o of D(after q=o)) / c_q. Choose the greatest positive score; break ties by cost then identifier. A null selection means no useful one-step query, not that all possible combinations of queries are useless.

Queries may constrain only an externally attestable boundary amount, such as an authoritative upstream certificate. They may not pretend to reveal an arbitrary allocation inside a mixed account. Outcome partition completeness is validated. Costs and the existence of a usable evidence source are supplied assumptions; production authentication and permissions are not implemented.

Certificate: save input evidence, cohort/snapshot identity, threshold, version, both endpoint assignments, solver version and canonical SHA-256 digest. Verify integer capacities, conservation, objective totals and absence of a negative residual cycle for each endpoint objective. The residual check certifies optimality without rerunning network_simplex. Hashes do not establish source truth or resist an administrator who rewrites evidence and recomputes the digest.

Implementation boundary: app/services/joint_funding.py provides analyze, verify, rank_evidence and apply_evidence. The CLI is scripts/run_joint_funding.py. This is an offline prototype; live transfers, alert thresholds and the database schema are unchanged. Incremental optimization, learned query probabilities, bank connectors, automated holds and a trained fraud classifier using the new features are not implemented.

## 8. Experimental validation results

Correctness: 250 seeded small ledgers (seeds 0-249) were checked against independent exhaustive enumeration of all feasible integer allocations. All 250 matched exactly. The new test module passed 272 tests. The complete repository suite passed 394 tests with one skip; PostgreSQL-specific behavior was not established by this run. These counts are software validation, not fraud-detection accuracy.

Split/merge example: INR 10,000 of other opening funds plus INR 10,000 of cohort funds is split into two INR 10,000 payments. Each recipient separately has [0, 10,000] cohort holdings. Together they have [10,000, 10,000]. After both forward everything to a zero-balance recipient, that recipient also has [10,000, 10,000].

Evidence-selection experiment: 100 constructed cases, one useful source-boundary query and one disconnected higher-width distractor, equal cost and a one-query budget. The proposed selector resolved the funding condition for every outcome in 100/100 cases; widest-boundary selection did so in 0/100; seeded random selection in 40/100 (uniform-random expectation: 50/100). A reachability filter followed by widest-boundary selection also achieved 100/100. This intentionally narrow experiment establishes behavior, not superiority over a strong baseline.

Measured local timing includes certificate verification and counterfactual solves where applicable. Hardware architecture: arm64; Python 3.13.4; NetworkX 3.7. Small-ledger analysis p50/p95: 0.4281/0.4964 ms. Two-query selection p50/p95: 1.2623/1.4884 ms. These tiny synthetic workloads exclude real data retrieval and are not production latency estimates.

Negative and integrity checks cover overdrafts, incomplete inputs, duplicate targets/evidence, floating monetary values, invalid query partitions, attempts to query internal allocations, digest tampering and feasible-but-nonoptimal endpoint substitution. Large integer amounts remain exact. Irreducible fungibility can correctly produce no recommended query.

Not measured: fraud precision/recall, false alerts on real merchants, actual investigator effort, real retrieval savings, incremental speedup, or legal novelty. No customer dataset was used. Results and example inputs are saved under docs/evaluation/joint_funding_*.json; reproduction commands appear below.

## 9. Aspects proposed for protection

Candidate aspect for professional assessment: the operational sequence of computing jointly feasible terminal-funding intervals, detecting review-boundary ambiguity, evaluating exhaustive outcomes of obtainable boundary-evidence queries, selecting by worst-case decision benefit per cost, and issuing a verified updated certificate.

Potential narrower implementation detail: explicit separation of factual boundary uncertainty from unobservable internal allocation choices, combined with refusal to acquire evidence when no positive one-step benefit is certified. This is a candidate claim focus, not a conclusion that the distinction is new or non-obvious.

Do not claim exclusive novelty in network flows, min-cost circulation, integer arithmetic, negative-cycle optimality checks, hashing, generic active acquisition, graph fraud detection, FIFO alternatives, or split/merge tracing. Adding these known parts is not itself evidence of an inventive step.

Gate status: technical proof of concept PASS within stated assumptions; all ten disclosure topics ANSWERED; improvement over strong baselines NOT DEMONSTRATED; novelty/inventive step UNRESOLVED; jurisdictional eligibility and freedom to operate NOT ASSESSED. No patent application has been filed or submitted through this work.

Before filing: obtain a professional claim chart across cited families and citations, search robust attribution/network tomography/active diagnosis/database provenance beyond fraud terminology, test against stronger query policies on withheld realistic cases, and document an actual technical effect. If filing in India, review the official patent requirements and current CRI guidelines [L1-L2]. Human inventorship, ownership and disclosure history require the actual contributors' records; they are not inferred from this draft.

## 10. Technology readiness level

TRL 3 - experimental proof of concept (provisional self-assessment). Executable algorithms, synthetic demonstrations, oracle checks and test evidence exist. No integrated bank pilot, relevant operational environment, production qualification or real-customer performance validation has occurred. TRL 4-9 would overstate the current evidence.

## Reproduce the validation

```bash
.venv/bin/python -m pytest tests/test_joint_funding.py -q
.venv/bin/python -m scripts.evaluate_joint_funding
.venv/bin/python -m scripts.run_joint_funding docs/evaluation/joint_funding_example.json docs/evaluation/joint_funding_certificate.json
```

[L1: IP India patent basics](https://ipindia.gov.in/basics-of-patents)

[L2: Official CRI guidelines catalog](https://ipindia.gov.in/resource/patents-resources-guidelines)
