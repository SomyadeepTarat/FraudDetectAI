"""Offline research prototype: exact joint bounds and decision-directed evidence.

All monetary values are integer minor units. One currency, one cohort, complete
ordered internal ledger, no overdrafts or external withdrawals. Targets are final
account holdings, so serial transfers cannot double-count the same funds.
"""

import hashlib
import json
from copy import deepcopy
from fractions import Fraction

import networkx as nx

VERSION = "joint-funding-v1"


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError("Expected an integer minor-unit value in range")
    return value


def _name(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Expected a nonempty identifier")
    return value


def _digest(value):
    return hashlib.sha256(
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode()
    ).hexdigest()


def build_network(ledger):
    """Validate a complete snapshot and return immutable-by-convention edge facts."""
    for field in ("snapshot_id", "cohort_id", "currency"):
        _name(ledger[field])
    if ledger.get("complete") is not True:
        raise ValueError("INCOMPLETE: complete ordered ledger evidence is required")
    if not ledger["opening"]:
        raise ValueError("At least one opening account is required")
    balances, last, edges, ids = {}, {}, [], set()
    total = 0

    def add(u, v, amount, lower=0, upper=None, target=False):
        edges.append(
            {
                "id": len(edges),
                "u": u,
                "v": v,
                "lower": lower,
                "upper": amount if upper is None else upper,
                "target": target,
            }
        )

    def boundary(record):
        low, high = _integer(record["lower"]), _integer(record["upper"])
        if not low <= high <= record["amount"]:
            raise ValueError("Invalid boundary attribution interval")
        return low, high

    def record_id(record):
        key = _name(record["id"])
        if key in ids:
            raise ValueError("Duplicate evidence identifier")
        ids.add(key)

    for index, record in enumerate(ledger["opening"]):
        record_id(record)
        account = _name(record["account"])
        if account in balances:
            raise ValueError("Duplicate opening account")
        amount = _integer(record["amount"])
        balances[account], last[account] = amount, f"opening:{index}"
        add("root", last[account], amount, *boundary(record))
        total += amount

    for index, record in enumerate(ledger["movements"]):
        record_id(record)
        amount = _integer(record["amount"], 1)
        dest, source = record["destination"], record["source"]
        if dest not in balances or (source is not None and source not in balances):
            raise ValueError("Unknown account or unsupported external withdrawal")
        if source == dest:
            raise ValueError("Self transfer is not supported")
        dest_node = f"credit:{index}"
        add(last[dest], dest_node, balances[dest])
        if source is None:
            add("root", dest_node, amount, *boundary(record))
            total += amount
        else:
            if "lower" in record or "upper" in record:
                raise ValueError(
                    "Internal fungible allocations cannot be asserted as evidence"
                )
            if amount > balances[source]:
                raise ValueError("Overdraft or inconsistent ledger")
            source_node = f"debit:{index}"
            add(last[source], source_node, balances[source] - amount)
            add(last[source], dest_node, amount)
            balances[source] -= amount
            last[source] = source_node
        balances[dest] += amount
        last[dest] = dest_node

    targets = ledger["targets"]
    if (
        not targets
        or len(set(targets)) != len(targets)
        or not set(targets) <= balances.keys()
    ):
        raise ValueError("Targets must be distinct known final accounts")
    for account, amount in balances.items():
        add(last[account], "sink", amount, target=account in targets)
    add("sink", "root", total)
    return edges


def _optimize(edges, sign):
    graph = nx.MultiDiGraph()
    for edge in edges:
        u, v, low, high = edge["u"], edge["v"], edge["lower"], edge["upper"]
        for node in (u, v):
            if node not in graph:
                graph.add_node(node, demand=0)
        graph.nodes[u]["demand"] += low
        graph.nodes[v]["demand"] -= low
        graph.add_edge(
            u,
            v,
            key=edge["id"],
            capacity=high - low,
            weight=sign if edge["target"] else 0,
        )
    try:
        _, flow = nx.network_simplex(graph)
    except nx.NetworkXUnfeasible as exc:
        raise ValueError("Inconsistent funding evidence") from exc
    witness = [edge["lower"] + flow[edge["u"]][edge["v"]][edge["id"]] for edge in edges]
    return sum(x for edge, x in zip(edges, witness) if edge["target"]), witness


def _check_endpoint(edges, witness, sign, claimed):
    """Integer feasibility plus no negative residual cycle certifies optimality."""
    if len(witness) != len(edges):
        return False
    balance, residual = {}, nx.DiGraph()

    def residual_edge(u, v, weight):
        if not residual.has_edge(u, v) or weight < residual[u][v]["weight"]:
            residual.add_edge(u, v, weight=weight)

    for edge, value in zip(edges, witness):
        if type(value) is not int or not edge["lower"] <= value <= edge["upper"]:
            return False
        u, v = edge["u"], edge["v"]
        balance[u] = balance.get(u, 0) - value
        balance[v] = balance.get(v, 0) + value
        cost = sign if edge["target"] else 0
        if value < edge["upper"]:
            residual_edge(u, v, cost)
        if value > edge["lower"]:
            residual_edge(v, u, -cost)
    objective = sum(x for edge, x in zip(edges, witness) if edge["target"])
    return (
        not any(balance.values())
        and objective == claimed
        and not nx.negative_edge_cycle(residual, weight="weight")
    )


def funding_condition(lower, upper, threshold):
    _integer(threshold, 1)
    return (
        "MET"
        if lower >= threshold
        else "NOT_MET"
        if upper < threshold
        else "UNRESOLVED"
    )


def analyze(ledger, threshold):
    """Return a self-contained, replayable research certificate, never fraud probability."""
    edges = build_network(ledger)
    lower, low_witness = _optimize(edges, 1)
    upper, high_witness = _optimize(edges, -1)
    result = {
        "lower": lower,
        "upper": upper,
        "condition": funding_condition(lower, upper, threshold),
    }
    certificate = {
        "version": VERSION,
        "solver": f"networkx-{nx.__version__}-network-simplex",
        "ledger": deepcopy(ledger),
        "threshold": threshold,
        "result": result,
        "lower_witness": low_witness,
        "upper_witness": high_witness,
    }
    certificate["digest"] = _digest(certificate)
    if not verify(certificate):
        raise RuntimeError("Certificate verification failed")
    return certificate


def verify(certificate):
    """Verify evidence binding and endpoint optimality without rerunning the optimizer.

    This does not authenticate the supplied ledger or protect against an author
    changing evidence and recomputing its digest. Use an external trusted snapshot.
    """
    try:
        payload = {k: v for k, v in certificate.items() if k != "digest"}
        if (
            certificate["version"] != VERSION
            or _digest(payload) != certificate["digest"]
        ):
            return False
        edges, result = build_network(certificate["ledger"]), certificate["result"]
        lower, upper = _integer(result["lower"]), _integer(result["upper"])
        return (
            lower <= upper
            and result["condition"]
            == funding_condition(lower, upper, certificate["threshold"])
            and _check_endpoint(edges, certificate["lower_witness"], 1, lower)
            and _check_endpoint(edges, certificate["upper_witness"], -1, upper)
        )
    except (KeyError, TypeError, ValueError, nx.NetworkXException):
        return False


def _boundary_record(ledger, record_id):
    for record in ledger["opening"]:
        if record["id"] == record_id:
            return record
    for record in ledger["movements"]:
        if record["id"] == record_id and record["source"] is None:
            return record
    raise ValueError(
        "Evidence can constrain only an external boundary, not internal fungibility"
    )


def _validate_query(ledger, query):
    _name(query["id"])
    _name(query["evidence_reference"])
    _integer(query["cost"], 1)
    record = _boundary_record(ledger, query["record_id"])
    cursor = record["lower"]
    if not query["outcomes"]:
        raise ValueError("A query requires exhaustive outcomes")
    for low, high in query["outcomes"]:
        _integer(low)
        _integer(high)
        if low != cursor or high < low or high > record["upper"]:
            raise ValueError(
                "Outcomes must partition the boundary interval without gaps or overlaps"
            )
        cursor = high + 1
    if cursor != record["upper"] + 1:
        raise ValueError("Outcomes omit possible evidence")


def apply_evidence(ledger, query, outcome_index):
    """Return a revised snapshot input; caller must authenticate the actual response."""
    build_network(ledger)
    _validate_query(ledger, query)
    _integer(outcome_index)
    if outcome_index >= len(query["outcomes"]):
        raise ValueError("Unknown query outcome")
    updated = deepcopy(ledger)
    record = _boundary_record(updated, query["record_id"])
    record["lower"], record["upper"] = query["outcomes"][outcome_index]
    updated.setdefault("evidence_updates", []).append(
        {
            "query_id": query["id"],
            "reference": query["evidence_reference"],
            "record_id": query["record_id"],
            "outcome": outcome_index,
        }
    )
    return updated


def rank_evidence(ledger, threshold, queries):
    """Greedy minimax decision-ambiguity reduction per cost; no learned probabilities.

    Each query supplies an exhaustive partition of an attestable boundary amount.
    All outcomes are solved, including the least helpful. This is not a globally
    optimal multi-query policy and does not perform external data acquisition.
    """
    base = analyze(ledger, threshold)
    start = base["result"]
    width = start["upper"] - start["lower"] if start["condition"] == "UNRESOLVED" else 0
    rows, ids = [], set()
    for query in queries:
        _validate_query(ledger, query)
        if query["id"] in ids:
            raise ValueError("Duplicate query identifier")
        ids.add(query["id"])
        outcomes = [
            analyze(apply_evidence(ledger, query, i), threshold)["result"]
            for i in range(len(query["outcomes"]))
        ]
        worst = max(
            r["upper"] - r["lower"] if r["condition"] == "UNRESOLVED" else 0
            for r in outcomes
        )
        gain = width - worst
        score = Fraction(gain, query["cost"])
        rows.append(
            {
                "query": deepcopy(query),
                "outcomes": outcomes,
                "guaranteed_ambiguity_reduction": gain,
                "score_numerator": score.numerator,
                "score_denominator": score.denominator,
                "all_outcomes_resolve": all(
                    r["condition"] != "UNRESOLVED" for r in outcomes
                ),
            }
        )
    rows.sort(
        key=lambda r: (
            -Fraction(r["score_numerator"], r["score_denominator"]),
            r["query"]["cost"],
            r["query"]["id"],
        )
    )
    selected = (
        rows[0]["query"]["id"]
        if rows and rows[0]["guaranteed_ambiguity_reduction"] > 0
        else None
    )
    report = {
        "version": VERSION,
        "policy": "minimax-unresolved-width-per-cost-v1",
        "base_certificate_digest": base["digest"],
        "selected_query": selected,
        "reason": "Positive worst-case decision-ambiguity reduction"
        if selected
        else "No positive one-step decision benefit; ambiguity may be irreducible or require joint queries",
        "ranking": rows,
    }
    report["digest"] = _digest(report)
    return report
