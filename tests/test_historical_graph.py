import pandas as pd

from fraudgraph.features.historical_graph import historical_graph_features


def test_strict_prior_steps_and_label_independence():
    frame = pd.DataFrame(
        {
            "step": [1, 1, 2, 3],
            "nameOrig": ["a", "a", "a", "b"],
            "nameDest": ["b", "b", "b", "a"],
            "amount": [10, 20, 5, 1],
            "isFraud": [0, 1, 0, 1],
        }
    )
    result = historical_graph_features(frame)
    assert list(result.sender_receiver_edge_transaction_count) == [0, 0, 2, 0]
    assert result.loc[2, "sender_total_sent_amount"] == 30
    assert result.loc[3, "sender_total_received_amount"] == 35
    changed = frame.copy()
    changed["isFraud"] = 1 - changed["isFraud"]
    changed.loc[3, "amount"] = 1000
    cols = [c for c in result if c.startswith(("sender_", "receiver_"))]
    pd.testing.assert_frame_equal(
        result[cols], historical_graph_features(changed)[cols]
    )
