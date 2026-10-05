"""Adapter around the existing fitted sklearn PaySim pipeline."""

import hashlib
from functools import cached_property

import numpy as np
import pandas as pd

from fraudgraph.data.preprocess import create_basic_transaction_features
from fraudgraph.models.model_registry import load_model
from fraudgraph.utils.paths import resolve_project_path


class ModelInference:
    def __init__(self, model_path):
        self.path = resolve_project_path(model_path)

    @cached_property
    def model(self):
        return load_model(self.path)

    @cached_property
    def version(self):
        digest = hashlib.sha256()
        with self.path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

    def predict(self, transaction):
        frame = create_basic_transaction_features(
            pd.DataFrame(
                [
                    {
                        # PaySim step denotes elapsed hours; online service uses UTC hour-of-day.
                        "step": transaction.transaction_timestamp.hour + 1,
                        "type": transaction.transaction_type,
                        "amount": float(transaction.amount),
                        "oldbalanceOrg": float(transaction.balance_before),
                        "newbalanceOrig": float(transaction.balance_after),
                        "oldbalanceDest": float(transaction.destination_balance_before),
                        "newbalanceDest": float(transaction.destination_balance_after),
                    }
                ]
            )
        )
        columns = list(self.model.feature_names_in_)
        missing = set(columns) - set(frame.columns)
        if missing:
            raise ValueError(
                "Online transfers require a baseline PaySim model; graph features need a separate online graph adapter"
            )
        probability = float(
            self.model.predict_proba(frame[columns])[
                0, list(self.model.classes_).index(1)
            ]
        )
        if not np.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("Model returned an invalid fraud probability")
        return probability, self.path.stem, self.version
