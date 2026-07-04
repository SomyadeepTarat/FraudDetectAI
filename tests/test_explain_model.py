import pandas as pd
import pytest

from fraudgraph.explainability.explain_model import (
    create_transaction_explanations,
    explain_transaction_with_rules,
    get_numeric_value,
    get_string_value,
)


def create_explanation_rules() -> dict[str, float]:
    return {
        "high_probability_threshold": 0.75,
        "high_amount_ratio_threshold": 0.80,
        "high_receiver_fraud_rate_threshold": 0.20,
        "high_sender_fraud_rate_threshold": 0.20,
        "high_edge_fraud_rate_threshold": 0.20,
        "high_receiver_in_degree_threshold": 10,
        "high_sender_out_degree_threshold": 10,
    }


def create_sample_scored_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "nameOrig": ["C1", "C2", "C3"],
            "nameDest": ["C4", "C5", "C6"],
            "type": ["TRANSFER", "PAYMENT", "CASH_OUT"],
            "amount": [1000.0, 50.0, 900.0],
            "fraud_probability": [0.95, 0.10, 0.80],
            "predicted_fraud": [1, 0, 1],
            "risk_band": ["CRITICAL", "LOW", "CRITICAL"],
            "isFraud": [1, 0, 1],
            "amount_to_old_origin_balance_ratio": [1.0, 0.1, 0.9],
            "is_origin_balance_emptied": [1, 0, 1],
            "receiver_incoming_fraud_rate": [0.5, 0.0, 0.3],
            "sender_outgoing_fraud_rate": [0.4, 0.0, 0.1],
            "sender_receiver_edge_fraud_rate": [1.0, 0.0, 0.8],
            "receiver_in_degree": [20.0, 1.0, 12.0],
            "sender_out_degree": [15.0, 1.0, 5.0],
        }
    )


def test_get_numeric_value_returns_existing_value() -> None:
    row = pd.Series({"amount": 100.0})

    assert get_numeric_value(row, "amount") == pytest.approx(100.0)


def test_get_numeric_value_returns_default_for_missing_value() -> None:
    row = pd.Series({"amount": 100.0})

    assert get_numeric_value(row, "missing", default=-1.0) == pytest.approx(-1.0)


def test_get_string_value_returns_existing_value() -> None:
    row = pd.Series({"type": "TRANSFER"})

    assert get_string_value(row, "type") == "TRANSFER"


def test_get_string_value_returns_default_for_missing_value() -> None:
    row = pd.Series({"type": "TRANSFER"})

    assert get_string_value(row, "missing") == "UNKNOWN"


def test_explain_transaction_with_rules_generates_reasons() -> None:
    dataframe = create_sample_scored_dataframe()
    row = dataframe.iloc[0]

    reasons = explain_transaction_with_rules(
        row=row,
        explanation_rules=create_explanation_rules(),
    )

    assert any("high fraud probability" in reason for reason in reasons)
    assert any("balance was emptied" in reason for reason in reasons)
    assert any("Receiver has a high incoming fraud rate" in reason for reason in reasons)
    assert any("sender-receiver relationship" in reason for reason in reasons)


def test_create_transaction_explanations_returns_top_risky_transactions() -> None:
    dataframe = create_sample_scored_dataframe()

    explanations = create_transaction_explanations(
        scored_dataframe=dataframe,
        explanation_rules=create_explanation_rules(),
        top_n_transactions=2,
    )

    assert len(explanations) == 2
    assert explanations[0]["sender"] == "C1"
    assert explanations[0]["fraud_probability"] == pytest.approx(0.95)
    assert explanations[1]["sender"] == "C3"
    assert explanations[1]["fraud_probability"] == pytest.approx(0.80)
    assert len(explanations[0]["reasons"]) > 0


def test_create_transaction_explanations_rejects_invalid_top_n() -> None:
    dataframe = create_sample_scored_dataframe()

    with pytest.raises(ValueError, match="top_n_transactions must be greater"):
        create_transaction_explanations(
            scored_dataframe=dataframe,
            explanation_rules=create_explanation_rules(),
            top_n_transactions=0,
        )