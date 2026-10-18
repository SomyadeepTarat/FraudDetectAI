"""Reproduce proof-of-concept results; no real fraud-detection claims."""

import json
import platform
import random
import statistics
from copy import deepcopy
from pathlib import Path
from time import perf_counter

import networkx as nx

from app.services.joint_funding import analyze, apply_evidence, rank_evidence, verify
from scripts.joint_funding_cases import (
    enumerate_bounds,
    query_case,
    split_case,
    tiny_case,
)


def main():
    timings, oracle_matches = [], 0
    for seed in range(250):
        ledger = tiny_case(seed)
        start = perf_counter()
        certificate = analyze(ledger, 1)
        timings.append(1000 * (perf_counter() - start))
        oracle = enumerate_bounds(ledger)
        result = certificate["result"]
        assert (result["lower"], result["upper"]) == oracle
        assert verify(certificate)
        oracle_matches += 1

    split = split_case()
    joint = analyze(split, 1)
    marginal = []
    for account in ("B", "C"):
        one = deepcopy(split)
        one["targets"] = [account]
        marginal.append(analyze(one, 1)["result"])
    merged = deepcopy(split)
    merged["targets"] = ["D"]
    for account in ("B", "C"):
        merged["movements"].append(
            {
                "id": f"merge-{account}",
                "source": account,
                "destination": "D",
                "amount": 1_000_000,
            }
        )

    resolved = {
        "decision_directed": 0,
        "widest_boundary": 0,
        "random_query_seed_1729": 0,
        "reachability_filter_then_widest_boundary": 0,
    }
    rng, query_timings = random.Random(1729), []
    for seed in range(100):
        ledger, threshold, queries = query_case(seed)
        start = perf_counter()
        report = rank_evidence(ledger, threshold, queries)
        query_timings.append(1000 * (perf_counter() - start))
        graph = nx.DiGraph()
        graph.add_nodes_from(r["account"] for r in ledger["opening"])
        graph.add_edges_from(
            (r["source"], r["destination"])
            for r in ledger["movements"]
            if r["source"] is not None
        )
        by_id = {r["id"]: r for r in ledger["opening"]}
        relevant = [
            q
            for q in queries
            if any(
                nx.has_path(graph, by_id[q["record_id"]]["account"], t)
                for t in ledger["targets"]
            )
        ]
        filtered = max(
            relevant,
            key=lambda q: (
                by_id[q["record_id"]]["upper"] - by_id[q["record_id"]]["lower"]
            ),
        )
        choices = {
            "decision_directed": next(
                q for q in queries if q["id"] == report["selected_query"]
            ),
            "widest_boundary": queries[1],
            "random_query_seed_1729": rng.choice(queries),
            "reachability_filter_then_widest_boundary": filtered,
        }
        for policy, query in choices.items():
            # A case counts only when EVERY supplied possible outcome resolves the condition.
            conditions = [
                analyze(apply_evidence(ledger, query, i), threshold)["result"][
                    "condition"
                ]
                for i in range(len(query["outcomes"]))
            ]
            resolved[policy] += all(c != "UNRESOLVED" for c in conditions)

    def latency(values):
        ordered = sorted(values)
        return {
            "p50_ms": round(statistics.median(values), 4),
            "p95_ms": round(ordered[int(0.95 * (len(ordered) - 1))], 4),
        }

    report = {
        "status": "SYNTHETIC_PROOF_OF_CONCEPT_NOT_FRAUD_ACCURACY",
        "runtime": {
            "python": platform.python_version(),
            "networkx": nx.__version__,
            "machine": platform.machine(),
        },
        "oracle": {
            "cases": 250,
            "seed_range": [0, 249],
            "exact_matches": oracle_matches,
            "method": "Independent enumeration of every integer allocation per generated ledger",
            "analyze_including_certificate_verification": latency(timings),
        },
        "split_example_minor_units": {
            "joint": joint["result"],
            "marginal": marginal,
            "merged": analyze(merged, 1)["result"],
        },
        "query_microbenchmark": {
            "cases": 100,
            "seed_range": [0, 99],
            "query_budget": 1,
            "cost_each": 1,
            "cases_resolved_for_every_query_outcome": resolved,
            "uniform_random_expected_resolved_cases": 50,
            "selection_including_counterfactual_solves": latency(query_timings),
            "limitation": "Deliberately constructed relevant-versus-disconnected-distractor family. A simple reachability baseline ties the proposed method. Not representative banking data; no demonstrated superiority to strong baselines, trained EDDI or production models.",
        },
        "not_measured": [
            "fraud precision/recall",
            "real analyst workload",
            "network or bank retrieval cost",
            "production latency",
            "incremental solver speedup",
            "patent novelty",
        ],
    }
    output = Path("docs/evaluation")
    output.mkdir(parents=True, exist_ok=True)
    (output / "joint_funding_evaluation.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    ledger, threshold, queries = query_case(0)
    (output / "joint_funding_example.json").write_text(
        json.dumps(
            {"ledger": ledger, "threshold": threshold, "queries": queries}, indent=2
        )
        + "\n"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
