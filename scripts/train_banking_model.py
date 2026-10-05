"""Train the existing baseline RF on a bounded, genuine PaySim sample.

No synthetic labels or fabricated fraud probabilities are used. This is a local
integration artifact; use the full existing training/evaluation pipeline for research.
"""

import argparse
import json

import pandas as pd
from sklearn.model_selection import train_test_split

from fraudgraph.data.preprocess import clean_paysim_data
from fraudgraph.features.transaction_features import save_feature_columns
from fraudgraph.models.train_baselines import (
    build_random_forest_pipeline,
    train_and_evaluate_model,
)
from fraudgraph.utils.config import load_yaml_config
from fraudgraph.utils.paths import resolve_project_path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dataset", default="data/raw/PS_20174392719_1491204439457_log.csv"
    )
    parser.add_argument("--normal-rows", type=int, default=20000)
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing baseline artifact"
    )
    args = parser.parse_args()
    if args.normal_rows < 100:
        parser.error("--normal-rows must be at least 100")
    if (
        resolve_project_path("models/baseline/random_forest.joblib").exists()
        and not args.force
    ):
        print(
            "Existing baseline artifact preserved. Use MODEL_PATH to select it, or --force to deliberately retrain."
        )
        return
    config = load_yaml_config()
    normal_parts, fraud_parts = [], []
    remaining = args.normal_rows
    for chunk in pd.read_csv(resolve_project_path(args.dataset), chunksize=200000):
        fraud_parts.append(chunk[chunk.isFraud == 1])
        if remaining > 0:
            sample = chunk[chunk.isFraud == 0].head(remaining)
            normal_parts.append(sample)
            remaining -= len(sample)
    frame = clean_paysim_data(pd.concat(normal_parts + fraud_parts, ignore_index=True))
    numeric = config["modeling"]["numeric_features"]
    categorical = config["modeling"]["categorical_features"]
    X_train, X_test, y_train, y_test = train_test_split(
        frame[numeric + categorical],
        frame.isFraud,
        test_size=0.2,
        random_state=42,
        stratify=frame.isFraud,
    )
    pipeline = build_random_forest_pipeline(numeric, categorical, 42, 100, 12, 5)
    metrics = train_and_evaluate_model(
        "banking_random_forest",
        pipeline,
        X_train,
        X_test,
        y_train,
        y_test,
        "models/baseline/random_forest.joblib",
    )
    save_feature_columns(
        numeric, categorical, "models/artifacts/baseline_feature_columns.json"
    )
    output = resolve_project_path("reports/metrics/banking_model_metadata.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    from app.db.models import utcnow

    output.write_text(
        json.dumps(
            {
                "training_date": utcnow().isoformat(),
                "dataset": args.dataset,
                "normal_sampling": "first N normal rows; all fraud rows",
                "rows": len(frame),
                "warning": "Enriched class sample; metrics/probabilities do not establish deployment calibration",
                "metrics": metrics,
            },
            indent=2,
        )
    )
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
