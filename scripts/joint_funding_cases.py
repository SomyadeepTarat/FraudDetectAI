"""Small synthetic fixtures and an independent enumerative accounting oracle."""

import random
from itertools import product


def split_case():
    return {
        "snapshot_id": "synthetic-split-1",
        "cohort_id": "complaint-demo",
        "currency": "INR",
        "complete": True,
        "opening": [
            {
                "id": f"open-{a}",
                "account": a,
                "amount": 1_000_000 if a == "A" else 0,
                "lower": 0,
                "upper": 0,
            }
            for a in "ABCD"
        ],
        "movements": [
            {
                "id": "receipt",
                "source": None,
                "destination": "A",
                "amount": 1_000_000,
                "lower": 1_000_000,
                "upper": 1_000_000,
            },
            {"id": "split-B", "source": "A", "destination": "B", "amount": 1_000_000},
            {"id": "split-C", "source": "A", "destination": "C", "amount": 1_000_000},
        ],
        "targets": ["B", "C"],
    }


def query_case(seed=0):
    rng = random.Random(seed)
    amount = rng.randint(10, 200)
    threshold = rng.randint(1, amount)
    ledger = {
        "snapshot_id": f"synthetic-query-{seed}",
        "cohort_id": "boundary-demo",
        "currency": "INR",
        "complete": True,
        "opening": [
            {
                "id": "relevant",
                "account": "A",
                "amount": amount,
                "lower": 0,
                "upper": amount,
            },
            {
                "id": "distractor",
                "account": "B",
                "amount": amount * 10,
                "lower": 0,
                "upper": amount * 10,
            },
            {"id": "empty", "account": "C", "amount": 0, "lower": 0, "upper": 0},
        ],
        "movements": [
            {"id": "forward", "source": "A", "destination": "C", "amount": amount}
        ],
        "targets": ["C"],
    }
    queries = [
        {
            "id": "relevant-query",
            "record_id": "relevant",
            "cost": 1,
            "evidence_reference": "SIMULATED upstream boundary certificate",
            "outcomes": [[0, threshold - 1], [threshold, amount]],
        },
        {
            "id": "distractor-query",
            "record_id": "distractor",
            "cost": 1,
            "evidence_reference": "SIMULATED unrelated boundary certificate",
            "outcomes": [[0, amount * 5], [amount * 5 + 1, amount * 10]],
        },
    ]
    return ledger, threshold, queries


def tiny_case(seed):
    rng = random.Random(seed)
    opening, balances = [], {}
    for account in "ABC":
        amount = rng.randint(0, 3)
        low = rng.randint(0, amount)
        high = rng.randint(low, amount)
        opening.append(
            {
                "id": f"open-{account}",
                "account": account,
                "amount": amount,
                "lower": low,
                "upper": high,
            }
        )
        balances[account] = amount
    movements = []
    for index in range(5):
        funded = [a for a, value in balances.items() if value]
        if not funded or rng.random() < 0.3:
            dest, amount = rng.choice("ABC"), rng.randint(1, 2)
            low = rng.randint(0, amount)
            movements.append(
                {
                    "id": f"tx-{index}",
                    "source": None,
                    "destination": dest,
                    "amount": amount,
                    "lower": low,
                    "upper": rng.randint(low, amount),
                }
            )
        else:
            source = rng.choice(funded)
            dest = rng.choice([a for a in "ABC" if a != source])
            amount = rng.randint(1, balances[source])
            balances[source] -= amount
            movements.append(
                {
                    "id": f"tx-{index}",
                    "source": source,
                    "destination": dest,
                    "amount": amount,
                }
            )
        balances[dest] += amount
    return {
        "snapshot_id": f"tiny-{seed}",
        "cohort_id": "oracle",
        "currency": "INR",
        "complete": True,
        "opening": opening,
        "movements": movements,
        "targets": rng.sample(list("ABC"), rng.randint(1, 3)),
    }


def enumerate_bounds(ledger):
    """Exhaust every possible tagged-unit allocation, with no graph optimizer."""
    accounts = [r["account"] for r in ledger["opening"]]
    index = {a: i for i, a in enumerate(accounts)}
    balances = [r["amount"] for r in ledger["opening"]]
    states = set(
        product(*(range(r["lower"], r["upper"] + 1) for r in ledger["opening"]))
    )
    for record in ledger["movements"]:
        dest = index[record["destination"]]
        amount, following = record["amount"], set()
        for state in states:
            if record["source"] is None:
                for tagged in range(record["lower"], record["upper"] + 1):
                    updated = list(state)
                    updated[dest] += tagged
                    following.add(tuple(updated))
            else:
                source = index[record["source"]]
                for tagged in range(
                    max(0, amount - (balances[source] - state[source])),
                    min(amount, state[source]) + 1,
                ):
                    updated = list(state)
                    updated[source] -= tagged
                    updated[dest] += tagged
                    following.add(tuple(updated))
        if record["source"] is not None:
            balances[index[record["source"]]] -= amount
        balances[dest] += amount
        states = following
    values = [sum(state[index[a]] for a in ledger["targets"]) for state in states]
    return min(values), max(values)
