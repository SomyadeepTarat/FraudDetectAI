"""Label-free graph features from strictly earlier time steps only.

PaySim does not resolve ordering within one hourly step. All rows in a step
observe the same prior graph; updates happen only after that step is scored.
"""

from collections import defaultdict

import pandas as pd


def historical_graph_features(frame):
    required = {"step", "nameOrig", "nameDest", "amount"}
    if not required <= set(frame):
        raise ValueError(f"Missing columns: {sorted(required - set(frame))}")
    if frame[list(required)].isna().any().any() or (frame["amount"] < 0).any():
        raise ValueError("Missing graph facts or negative amounts")
    frame = frame.reset_index(drop=True)
    incoming, outgoing = defaultdict(set), defaultdict(set)
    sent, received, nout, nin = (defaultdict(float) for _ in range(4))
    edges = defaultdict(lambda: [0.0, 0.0])
    results = [None] * len(frame)

    def node(account):
        return {
            "in_degree": float(len(incoming[account])),
            "out_degree": float(len(outgoing[account])),
            "total_degree": float(len(incoming[account]) + len(outgoing[account])),
            "total_sent_amount": sent[account],
            "total_received_amount": received[account],
            "outgoing_transaction_count": nout[account],
            "incoming_transaction_count": nin[account],
            "avg_sent_amount": sent[account] / nout[account] if nout[account] else 0.0,
            "avg_received_amount": received[account] / nin[account]
            if nin[account]
            else 0.0,
        }

    for _, group in frame.groupby("step", sort=True):
        for row in group.itertuples():
            source, dest = str(row.nameOrig), str(row.nameDest)
            features = {
                f"{prefix}_{k}": v
                for prefix, account in (("sender", source), ("receiver", dest))
                for k, v in node(account).items()
            }
            count, amount = edges[source, dest]
            features.update(
                sender_receiver_edge_transaction_count=count,
                sender_receiver_edge_total_amount=amount,
                sender_receiver_edge_avg_amount=amount / count if count else 0.0,
            )
            results[row.Index] = features
        for row in group.itertuples():
            source, dest, amount = (
                str(row.nameOrig),
                str(row.nameDest),
                float(row.amount),
            )
            outgoing[source].add(dest)
            incoming[dest].add(source)
            sent[source] += amount
            received[dest] += amount
            nout[source] += 1
            nin[dest] += 1
            edges[source, dest][0] += 1
            edges[source, dest][1] += amount
    return pd.concat([frame, pd.DataFrame(results)], axis=1)
