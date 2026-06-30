from pathlib import Path
from typing import Any

import joblib

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_parent_dir

logger = get_logger(__name__)


def save_model(model: Any, output_path: str | Path) -> Path:

    resolved_output_path = ensure_parent_dir(output_path)

    joblib.dump(model, resolved_output_path)

    logger.info("Saved model to: %s", resolved_output_path)

    return resolved_output_path


def load_model(model_path: str | Path) -> Any:

    resolved_model_path = Path(model_path)

    if not resolved_model_path.is_absolute():
        from fraudgraph.utils.paths import resolve_project_path

        resolved_model_path = resolve_project_path(model_path)

    if not resolved_model_path.exists():
        raise FileNotFoundError(f"Model artifact not found: {resolved_model_path}")

    model = joblib.load(resolved_model_path)

    logger.info("Loaded model from: %s", resolved_model_path)

    return model