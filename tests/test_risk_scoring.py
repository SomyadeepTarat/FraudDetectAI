import numpy as np
import pandas as pd
import pytest

from fraudgraph.models.risk_scoring import (
    assign_risk_band,
    create_risk_scoring_report,
    get_top_risky_transactions,
    score_transactions,
)


class DummyRiskModel:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return np.array(
            [
                [0.90, 0.10],
                [0.60, 0.40],
                [0.30, 0.70],
                [0.05, 0.95],
            ]
        )


def test_assign_risk_band_returns_expected_bands() -> None:
    assert assign_risk_band(0.10, 0.25, 0.50, 0.75) == "LOW"
    assert assign_risk_band(0.40, 0.25, 0.50, 0.75) == "MEDIUM"
    assert assign_risk_band(0.70, 0.25, 0.50, 0.75) == "HIGH"
    assert assign_risk_band(0.90, 0.25, 0.50, 0.75) == "CRITICAL"


def test_assign_risk_band_rejects_invalid_probability() -> None:
    with pytest.raises(ValueError, match="fraud_probability must be between"):
        assign_risk_band(1.5, 0.25, 0.50, 0.75)


def test_score_transactions_adds_scoring_columns() -> None:
    model = DummyRiskModel()
    dataframe = pd.DataFrame(
        {
            "amount": [100.0, 200.0, 300.0, 400.0],
            "type": ["PAYMENT", "TRANSFER", "CASH_OUT", "TRANSFER"],
            "isFraud": [0, 0, 1, 1],
        }
    )

    scored = score_transactions(
        model=model,
        dataframe=dataframe,
        feature_columns=["amount", "type"],
        decision_threshold=0.5,
        risk_band_config={
            "low_max": 0.25,
            "medium_max": 0.50,
            "high_max": 0.75,
        },
    )

    assert "fraud_probability" in scored.columns
    assert "predicted_fraud" in scored.columns
    assert "risk_band" in scored.columns
    assert set(scored["risk_band"]) == {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def test_create_risk_scoring_report_returns_expected_structure() -> None:
    scored_dataframe = pd.DataFrame(
        {
            "fraud_probability": [0.95, 0.70, 0.40, 0.10],
            "predicted_fraud": [1, 1, 0, 0],
            "risk_band": ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
            "isFraud": [1, 1, 0, 0],
        }
    )

    report = create_risk_scoring_report(
        scored_dataframe=scored_dataframe,
        target_column="isFraud",
        decision_threshold=0.5,
    )

    assert report["decision_threshold"] == pytest.approx(0.5)
    assert report["num_transactions_scored"] == 4
    assert report["risk_band_counts"] == {
        "CRITICAL": 1,
        "HIGH": 1,
        "MEDIUM": 1,
        "LOW": 1,
    }
    assert report["actual_fraud_rate_by_risk_band"]["CRITICAL"] == pytest.approx(1.0)


def test_get_top_risky_transactions_returns_highest_probability_rows() -> None:
    scored_dataframe = pd.DataFrame(
        {
            "transaction_id": [1, 2, 3],
            "fraud_probability": [0.20, 0.95, 0.70],
        }
    )

    top_rows = get_top_risky_transactions(
        scored_dataframe=scored_dataframe,
        top_n=2,
    )

    assert list(top_rows["transaction_id"]) == [2, 3]