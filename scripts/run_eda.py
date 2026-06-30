import pandas as pd

from fraudgraph.eda.eda_plots import generate_all_eda_plots
from fraudgraph.eda.eda_summary import create_eda_summary, save_eda_summary
from fraudgraph.utils.config import load_yaml_config
from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import resolve_project_path

logger = get_logger(__name__)


def main() -> None:

    config = load_yaml_config("configs/config.yaml")

    cleaned_data_path = config["data"]["interim_data_path"]
    target_column = config["target"]["name"]
    transaction_type_column = "type"

    eda_summary_output_path = config["eda"]["summary_output_path"]
    figures_dir = config["eda"]["figures_dir"]
    sample_size = int(config["eda"]["sample_size_for_plots"])
    random_seed = int(config["eda"]["random_seed"])

    resolved_cleaned_data_path = resolve_project_path(cleaned_data_path)

    if not resolved_cleaned_data_path.exists():
        raise FileNotFoundError(
            f"Cleaned dataset not found at {resolved_cleaned_data_path}. "
            "Run `python scripts/make_dataset.py` before running EDA."
        )

    logger.info("Loading cleaned dataset from: %s", resolved_cleaned_data_path)
    dataframe = pd.read_parquet(resolved_cleaned_data_path)
    logger.info("Loaded cleaned dataset with shape: %s", dataframe.shape)

    logger.info("Creating EDA summary.")
    eda_summary = create_eda_summary(
        dataframe=dataframe,
        target_column=target_column,
        transaction_type_column=transaction_type_column,
    )

    save_eda_summary(
        summary=eda_summary,
        output_path=eda_summary_output_path,
    )

    logger.info("Generating EDA plots.")
    saved_plot_paths = generate_all_eda_plots(
        dataframe=dataframe,
        target_column=target_column,
        transaction_type_column=transaction_type_column,
        output_dir=figures_dir,
        sample_size=sample_size,
        random_seed=random_seed,
    )

    for saved_plot_path in saved_plot_paths:
        logger.info("Generated plot: %s", saved_plot_path)

    logger.info("EDA pipeline completed successfully.")


if __name__ == "__main__":
    main()