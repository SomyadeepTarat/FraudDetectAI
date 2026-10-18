"""Run the existing offline artifact pipeline in dependency order."""

import os
import subprocess
import sys
from pathlib import Path

STEPS = (
    "make_dataset.py",
    "run_eda.py",
    "train_baseline.py",
    "build_transaction_graph.py",
    "create_graph_features.py",
    "train_graph_model.py",
    "evaluate_model.py",
    "tune_threshold.py",
    "explain_model.py",
)


def main():
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(root / "src"), str(root), env.get("PYTHONPATH", "")]
    )
    for step in STEPS:
        subprocess.run(
            [sys.executable, str(root / "scripts" / step)],
            cwd=root,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    main()
