from pathlib import Path

import pandas as pd

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def load_paysim_csv(file_path: str | Path) -> pd.DataFrame:
    resolved_path = resolve_project_path(file_path)

    if not resolved_path.exists():
        raise FileNotFoundError(
            "PaySim dataset was not found. "
            f"Expected file at: {resolved_path}. "
            "Download the dataset and place the CSV in data/raw/."
        )

    logger.info("Loading PaySim dataset from: %s", resolved_path)

    dataframe = pd.read_csv(resolved_path)

    if dataframe.empty:
        raise ValueError(f"Loaded dataset is empty: {resolved_path}")

    logger.info("Loaded dataset with shape: %s", dataframe.shape)

    return dataframe


def preview_dataframe(dataframe: pd.DataFrame, num_rows: int = 5) -> pd.DataFrame:
    if num_rows <= 0:
        raise ValueError("num_rows must be greater than 0.")

    return dataframe.head(num_rows)