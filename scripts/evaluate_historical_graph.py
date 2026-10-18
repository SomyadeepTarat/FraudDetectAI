"""Separate reproducible chronological PaySim experiment; preserves online artifacts."""

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import precision_recall_curve

from fraudgraph.data.preprocess import create_basic_transaction_features
from fraudgraph.features.historical_graph import historical_graph_features
from fraudgraph.models.evaluate import evaluate_binary_classifier
from fraudgraph.models.train_baselines import build_random_forest_pipeline
from fraudgraph.utils.config import load_yaml_config


def main():
    config = load_yaml_config("configs/config.yaml")
    rng = np.random.default_rng(20261016)
    selected = []
    raw = Path("data/raw/PS_20174392719_1491204439457_log.csv")
    for chunk in pd.read_csv(raw, chunksize=200000):
        selected.append(chunk.loc[rng.random(len(chunk)) < 0.02])
    frame = create_basic_transaction_features(pd.concat(selected, ignore_index=True))
    frame = historical_graph_features(frame.sort_values("step", kind="stable"))
    steps = sorted(frame.step.unique())
    cut1, cut2 = steps[int(len(steps) * 0.6)], steps[int(len(steps) * 0.8)]
    train, val, test = (
        frame[frame.step < cut1],
        frame[(frame.step >= cut1) & (frame.step < cut2)],
        frame[frame.step >= cut2],
    )
    for split in (train, val, test):
        if split.isFraud.nunique() != 2:
            raise ValueError(
                "Chronological split lacks both classes; increase sample fraction"
            )
    numeric = config["modeling"]["numeric_features"]
    categorical = config["modeling"]["categorical_features"]
    graph = config["graph_features"]["graph_feature_columns"]
    metrics = {}
    for name, features in (
        ("transaction_rf", numeric),
        ("historical_graph_rf", numeric + graph),
    ):
        model = build_random_forest_pipeline(
            features, categorical, 20261016, 100, 12, 5
        )
        model.fit(train[features + categorical], train.isFraud)
        val_prob = model.predict_proba(val[features + categorical])[:, 1]
        precision, recall, thresholds = precision_recall_curve(val.isFraud, val_prob)
        f1 = (
            2
            * precision[:-1]
            * recall[:-1]
            / np.maximum(precision[:-1] + recall[:-1], 1e-12)
        )
        threshold = float(thresholds[np.argmax(f1)])
        threshold = min(max(threshold, 1e-9), 1 - 1e-9)
        metrics[name] = {
            "threshold_selected_on_validation": threshold,
            "test": evaluate_binary_classifier(model, test[features + categorical], test.isFraud, threshold),
        }

    output = {
        "seed": 20261016,
        "sample_fraction": 0.02,
        "rows": len(frame),
        "split_steps": {"validation_start": int(cut1), "test_start": int(cut2)},
        "splits": {
            name: {"rows": len(split), "fraud": int(split.isFraud.sum())}
            for name, split in (("train", train), ("validation", val), ("test", test))
        },
        "metrics": metrics,
        "limitations": [
            "Random 2% naturally imbalanced row sample; prior graph is sampled, not complete.",
            "Features use strictly earlier hourly steps and no fraud labels.",
            "Two Random Forest baselines; no claim that all model families were retuned.",
            "PaySim hourly steps cannot validate the ten-minute FABC policy.",
        ],
    }
    path = Path("reports/metrics/historical_graph_evaluation.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
