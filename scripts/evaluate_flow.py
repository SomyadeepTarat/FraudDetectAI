"""Reproducible synthetic scenario evaluation; no real-bank performance claim.

Run with PYTHONPATH=src:. .venv/bin/python scripts/evaluate_flow.py.
Labels describe generated scenarios, not ground truth about criminal activity.
"""

import json
import random
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace

import numpy as np
from sklearn.metrics import average_precision_score, precision_score, recall_score

from app.services.features import behaviour_risk
from app.services.flow_bounds import funding_bounds
from app.services.inference import ModelInference
from app.settings import settings


def attribution(opening, events, target, method):
    lots = [[D(opening), False]]
    for side, amount in events + [("DEBIT", target)]:
        if side == "CREDIT":
            lots.append([D(amount), True])
            continue
        left, recent = D(amount), D(0)
        if method == "haircut":
            total = sum(x[0] for x in lots)
            for lot in lots:
                spent = D(amount) * lot[0] / total
                if lot[1]:
                    recent += spent
                lot[0] -= spent
        else:
            order = lots if method == "fifo" else list(reversed(lots))
            for lot in order:
                spent = min(left, lot[0])
                if lot[1]:
                    recent += spent
                lot[0] -= spent
                left -= spent
        result = recent
    return result


def main():
    rng = random.Random(20261016)
    rows, timings = [], []
    inference = ModelInference(settings.model_path)
    for i in range(1200):
        kind = ["pass_through", "merchant", "payroll", "family", "refund", "split"][
            i % 6
        ]
        receipts = [D(rng.randint(100, 5000)) for _ in range(rng.randint(1, 6))]
        opening = D(
            rng.randint(0, 1000)
            if kind == "pass_through"
            or (kind in ("merchant", "family", "payroll") and rng.random() < 0.5)
            else rng.randint(0, 100000)
        )
        events = [("CREDIT", a) for a in receipts]
        balance = opening + sum(receipts)
        prior = D(rng.randint(0, int(balance) // 2))
        if prior:
            events.append(("DEBIT", prior))
        target = D(rng.randint(1, int(balance - prior)))
        before = perf_counter()
        lower, upper = funding_bounds(opening, events, target)
        timings.append((perf_counter() - before) * 1000)
        attrs = {
            m: attribution(opening, events, target, m)
            for m in ("fifo", "lifo", "haircut")
        }
        for value in attrs.values():
            assert lower - D("0.00000001") <= value <= upper + D("0.00000001")
        fan_in = len(receipts) >= 3
        probability, _, _ = inference.predict(
            SimpleNamespace(
                transaction_timestamp=datetime(2026, 10, 16, 12, tzinfo=timezone.utc),
                transaction_type="TRANSFER",
                amount=target,
                balance_before=balance - prior,
                balance_after=balance - prior - target,
                destination_balance_before=D(0),
                destination_balance_after=target,
            )
        )
        behaviour, _ = behaviour_risk(
            {
                "transaction_count_last_10_minutes": 2 if prior else 1,
                "amount_deviation_from_customer_average": float(target / prior)
                if prior
                else None,
                "is_new_device": False,
                "location_changed": False,
                "unusual_transaction_hour": False,
            }
        )
        rows.append(
            {
                "scenario": kind,
                "label": int(kind == "pass_through"),
                "opening": str(opening),
                "events": [(s, str(a)) for s, a in events],
                "target": str(target),
                "lower": str(lower),
                "upper": str(upper),
                "scores": dict(
                    fabc=float(lower / target) if fan_in else 0,
                    ml=probability,
                    ml_behaviour=max(probability, 0.9 * behaviour),
                    upper=float(upper / target) if fan_in else 0,
                    no_counterparty=float(lower / target),
                    velocity=float(fan_in),
                    **{m: float(v / target) if fan_in else 0 for m, v in attrs.items()},
                ),
            }
        )
    labels = [r["label"] for r in rows]
    metrics = {}
    for method in rows[0]["scores"]:
        scores = [r["scores"][method] for r in rows]
        flags = [s >= 0.8 for s in scores]
        benign = sum(not y for y in labels)
        budget = sorted(range(len(rows)), key=lambda i: (-scores[i], i))[:120]
        metrics[method] = {
            "precision": precision_score(labels, flags, zero_division=0),
            "recall": recall_score(labels, flags, zero_division=0),
            "average_precision": average_precision_score(labels, scores),
            "false_alerts_per_1000_benign": 1000
            * sum(f and not y for f, y in zip(flags, labels))
            / benign,
            "recall_at_120_reviews": sum(labels[i] for i in budget) / sum(labels),
            "alerted_amount": str(
                sum(D(r["target"]) for r, f in zip(rows, flags) if f)
            ),
        }
    output = Path("reports/metrics")
    output.mkdir(parents=True, exist_ok=True)
    (output / "flow_scenarios.json").write_text(json.dumps(rows, indent=2))
    report = {
        "seed": 20261016,
        "n": len(rows),
        "threshold": 0.8,
        "review_budget": 120,
        "metrics": metrics,
        "scan_latency_ms": dict(
            zip(("p50", "p95", "p99"), np.percentile(timings, [50, 95, 99]).tolist())
        ),
        "limitations": [
            "Designed synthetic labels, not real-bank generalisation.",
            "No tuned parameters or trained classifiers; fixed report policy.",
            "Latency measures arithmetic only, not transfer, lock wait or PostgreSQL throughput.",
            "ML uses the existing PaySim artifact on synthetic target snapshots; this is a domain-mismatch stress test. Behaviour features assume one source customer, the listed earlier debit, no device/location anomaly and midday UTC. Historical graph has a separate chronological PaySim experiment.",
        ],
    }
    (output / "flow_evaluation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
