import numpy as np
import pandas as pd
import pytest

from fraudgraph.models.evaluate import evaluate_binary_classifier


class DummyProbabilityModel:
    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return np.array(
            [
                [0.90, 0.10],
                [0.20, 0.80],
                [0.70, 0.30],
                [0.10, 0.90],
            ]
        )


def test_evaluate_binary_classifier_returns_expected_metrics() -> None:
    model = DummyProbabilityModel()
    X_test = pd.DataFrame({"feature": [1, 2, 3, 4]})
    y_test = pd.Series([0, 1, 0, 1])

    metrics = evaluate_binary_classifier(
        model=model,
        X_test=X_test,
        y_test=y_test,
        threshold=0.5,
    )

    assert metrics["accuracy"] == pytest.approx(1.0)
    assert metrics["precision"] == pytest.approx(1.0)
    assert metrics["recall"] == pytest.approx(1.0)
    assert metrics["f1"] == pytest.approx(1.0)
    assert metrics["roc_auc"] == pytest.approx(1.0)
    assert metrics["average_precision"] == pytest.approx(1.0)

    assert metrics["confusion_matrix"] == {
        "true_negative": 2,
        "false_positive": 0,
        "false_negative": 0,
        "true_positive": 2,
    }


def test_evaluate_binary_classifier_rejects_invalid_threshold() -> None:
    model = DummyProbabilityModel()
    X_test = pd.DataFrame({"feature": [1, 2, 3, 4]})
    y_test = pd.Series([0, 1, 0, 1])

    with pytest.raises(ValueError, match="threshold must be between 0 and 1"):
        evaluate_binary_classifier(
            model=model,
            X_test=X_test,
            y_test=y_test,
            threshold=1.5,
        )