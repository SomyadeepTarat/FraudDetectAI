# Proposed research: evidence-directed joint funding bounds

18 October 2026. Research proposal, not an implemented algorithm or a patentability opinion. Preliminary public-source search; no exhaustive patent-family, prosecution-history, or freedom-to-operate assessment.

## Recommendation

Extend the existing Funding Ambiguity Bounds Certificate (FABC) into **evidence-directed joint funding bounds** for coordinated mule-account investigation. The system should answer:

1. Across all allocations consistent with the ledger, how much of a group of outgoing payments must originate in a specified source cohort?
2. If that result is ambiguous, which obtainable ledger evidence could resolve the review decision most efficiently?
3. Can the system retain a reproducible certificate of both the bounds and the reason for requesting that evidence?

The potential invention is the specific interaction between joint accounting constraints, decision-directed evidence acquisition, and incremental certificate maintenance. Graph learning, conservation equations, optimization, hashing, and active acquisition individually are established ideas. Combining them does not automatically create an inventive step.

## Fit with the current project

README.md reports that single-account FABC is implemented. app/services/flow_bounds.py computes exact marginal recent-funding intervals. Existing evidence persistence provides a starting point. The older PROJECT_NOVELTY_PROPOSAL.md still describes that work as proposed; it should not be interpreted as current implementation status.

The existing algorithm does not establish multi-account provenance or joint bounds for a set of payments. Do not multiply or add its marginal intervals to simulate those capabilities. Existing ML scores and flow evidence should remain distinct.

## Useful application

Prioritize investigations of instant-payment scam proceeds that split across mule accounts, mix with other balances, and converge at common recipients. Initially operate within one bank's complete internal ledger, after a complaint or a conventional model identifies a candidate source cohort. A cohort can instead contain merely recent receipts, but then the output describes recent funding, not fraudulent proceeds.

This is primarily an attribution and investigation improvement. It can support detection of related accounts; it cannot identify deceptive intent from accounting constraints alone or prevent the first scam without other signals.

### Worked example: a group can be informative when each payment is ambiguous

An account has INR 10,000 of other funds and receives INR 10,000 from a complaint-linked transfer. It then sends INR 10,000 to B and INR 10,000 to C, with no other movements.

Each outgoing transfer individually has a complaint-linked funding interval of [0, 10,000]. Neither recipient can individually be assigned a positive unavoidable amount. However, the pair jointly has interval [10,000, 10,000]: all complaint-linked money necessarily leaves in that pair. Summing marginal upper bounds would incorrectly suggest INR 20,000 of source funds.

If B and C subsequently send their entire balances to D, and both had zero opening balances and no other receipts, exactly INR 10,000 of the combined funds at D is attributable to the cohort. The system can flag a coordinated case while preserving uncertainty about the individual branches. This arithmetic example is illustrative, not a measured detection result.

## Algorithm specification

### 1. Construct a chronological network

Use an account-event node for every relevant balance change. Transfer edges connect sender and receiver events; carry edges retain balances between consecutive events. Assign capacities equal to posted transfer amounts and retained balances. Preserve causal ordering, opening balances, fees, reversals, and every modeled movement. Start with same-currency internal transfers and no overdrafts.

Choose a fixed evidence snapshot and a source cohort S, counting each source injection once. Specify which boundary funds are outside S and which have unknown cohort membership. Unobserved boundary flows must be represented by conservative constraints; if there is insufficient evidence even to bound them, return INCOMPLETE.

### 2. Compute joint bounds

Let z_e be the amount attributable to S on edge e, with 0 <= z_e <= capacity_e. Conserve attributable funds at every internal event node. Constrain source injections, opening balances, and boundary flows according to the evidence. The feasible set F contains every permitted allocation of those funds.

For a target set T, solve:

    L_T = min over z in F of sum(z_e for e in T)
    U_T = max over z in F of sum(z_e for e in T)

T must be a terminal frontier or another explicitly non-double-counting set. Summing serial transfers counts the same money repeatedly. For cumulative unique exit amounts, add absorbing exit nodes. Do not assume separate cohort solutions are jointly attainable when cohorts overlap; begin with one cohort versus all other funds.

A linear-programming reference implementation is adequate. Standard min-cost-flow reductions may improve runtime for the restricted network. These optimizers are not the novelty claim. Store feasible endpoint assignments and check conservation and objective values; retain dual bounds where available to verify optimality. Floating-point solver output requires tolerance-aware validation before any exact monetary claim.

### 3. Detect decision ambiguity

For a versioned review threshold tau on cohort funding, L_T >= tau establishes that the funding condition always holds; U_T < tau establishes that it cannot hold in the current model. Otherwise the condition is unresolved. Neither outcome alone proves fraud or innocence. An infeasible model indicates inconsistent evidence, not fraud.

Supply joint funding share, interval width, convergence structure, time-to-forward, source confidence, and completeness status to a separately evaluated classifier. Avoid treating every receipt as suspect. Source complaints must be available at the simulated decision time.

### 4. Request the evidence that could resolve the ambiguity

Enumerate obtainable queries, such as an authoritative opening-balance record, a complete intervening ledger segment, or a correction to a boundary transfer. Restrict requests to available permissions and data contracts. A query must constrain factual uncertainty; it cannot reveal the unique provenance of inherently fungible money.

Use differences between lower/upper witness allocations and boundary-constraint sensitivity to shortlist queries. For each shortlisted query, re-solve under plausible response outcomes. Rank by estimated reduction in decision loss divided by acquisition cost, including latency. Estimate outcome probabilities only from historical data available at decision time; without a validated response model, report scenario-dependent benefits rather than a fabricated expected gain.

Witness disagreement and dual sensitivity are heuristics for shortlisting, not guarantees of the globally optimal query. A two-stage query policy may outperform greedy selection when evidence is complementary. If all disagreement is irreducible fungibility, stop and report ambiguity instead of requesting useless records.

### 5. Update and certify

Bind the result to evidence identifiers, snapshot boundary, source-cohort version, target frontier, constraints, solver version, tolerances, and policy version. Record why the chosen query could change the review condition. After a response, update affected constraints and recompute; compare incremental results with full recomputation.

New evidence may shrink a fixed feasible set; new transactions or revised assumptions may change it. Do not promise monotone bounds across changing windows or ledgers. A hash supports replay comparison, not protection from privileged rewriting. Start with asynchronous investigation snapshots rather than putting a multi-account solver inside the existing transfer locks.

## Preliminary prior-art comparison

| Source | Established overlap | Candidate distinction requiring further search |
| --- | --- | --- |
| [FlowScope, AAAI 2020](https://cdn.aaai.org/ojs/5906/5906-13-9131-1-10-20200513.pdf) | Money-laundering detection through multi-step transaction flows | Joint fungible-funding intervals coupled to evidence requests; flow detection itself is old |
| [US20250045762A1](https://patents.google.com/patent/US20250045762A1/en) | Graph profiles, temporal activity, transaction-driven updates | A graph model or temporal feature update is insufficient novelty |
| [WO2026125967A1](https://patents.google.com/patent/WO2026125967A1/en) | Fraud tags, subsequent fund tracking, institutional coordination and responsive measures | Need detailed claim comparison; generic tracing and action are already disclosed |
| [EDDI](https://arxiv.org/abs/1809.11142) | Selecting high-value missing information | Evidence selection specifically from joint funding constraints and review-boundary ambiguity |
| [Pass-through templates, 2026 preprint](https://arxiv.org/abs/2609.20737) | Interpretable laundering detection in transaction graphs | Explainable pass-through detection alone is insufficient |

This shortlist does not establish that the proposed combination is absent from prior art. Next searches must include robust flow attribution, taint intervals, commingled funds, network tomography, active diagnosis, database provenance, decision-focused acquisition, and incremental optimization certificates. Search beyond fraud terminology. Inspect cited and citing documents, families, independent/dependent claims, and relevant dates. Also inspect US11854091B1, already identified in this repository's previous proposal.

## Experiments that would justify continuing

Compare transaction-only ML, historical graph features, existing FABC, joint bounds alone, and joint bounds plus evidence acquisition. Include random-query and generic uncertainty-query baselines at equal budgets.

Use chronological splits, delayed complaints/labels, separate scenario generators for training and testing, and held-out account groups. Construct both laundering patterns and matched legitimate merchant settlement, payroll, family pooling, and refunds. Test splitting, merging, looping, added legitimate funds, missing records, and delayed evidence. PaySim alone cannot establish the value of an evidence-request workflow.

Measure fraud-case recall at fixed false-positive and analyst-review budgets; precision-recall AUC; false alerts on matched benign cases; records fetched per resolved case; unresolved fraction; and p50/p95 latency. Count group alerts as group alerts, not as proof against every member. Separately verify interval correctness by exhaustive allocation on small integer ledgers, frontier double-counting checks, and full-versus-incremental equivalence.

Go/no-go rule: continue only if joint bounds add useful case-level evidence and query selection resolves more cases per evidence budget than the baselines. No improvement percentage is currently established. If the acquisition layer fails, retain the simpler joint-bounds research result without inflating the invention claim.

## Patent framing

Working disclosure title: **Decision-directed acquisition of ledger evidence using jointly feasible funding bounds in temporal payment networks.**

Candidate inventive sequence: construct shared-capacity chronological funding constraints; derive joint endpoint certificates for a non-double-counting target frontier; identify evidence constraints responsible for a review-boundary disagreement; select an obtainable query by decision benefit and cost; update the constraints and replayable certificate.

This is an invention hypothesis, not a drafted legal claim or assurance of novelty. A useful mathematical method, higher classifier accuracy, or a new name does not by itself establish patentability. If filing in India, assess novelty, inventive step, and computer-related-invention eligibility with the institution IP cell or patent counsel using [IP India's patent basics](https://ipindia.gov.in/basics-of-patents) and [current CRI guidelines](https://ipindia.gov.in/resource/patents-resources-guidelines). Document actual technical effects such as reduced ledger retrieval or recomputation cost at equal decision quality; these are proposed measurements, not established eligibility.

## First implementation scope

Build an offline, single-bank, single-currency reference solver with one source cohort and terminal target frontier. Reproduce the split-and-merge example, then implement simulated missing-record queries with known costs. Reuse FABC evidence conventions where appropriate. Only integrate into the analyst UI after correctness and controlled comparative results. Current application behavior is unchanged by this document.
