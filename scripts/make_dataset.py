from fraudgraph.data.load_data import load_paysim_csv
from fraudgraph.data.preprocess import clean_paysim_data, save_cleaned_data
from fraudgraph.data.validate_data import (
    assert_valid_dataset,
    create_validation_report,
    save_validation_report,
)
from fraudgraph.utils.config import load_yaml_config
from fraudgraph.utils.logger import get_logger

logger = get_logger(__name__)


def main() -> None:
    config = load_yaml_config("configs/config.yaml")

    raw_data_path = config["data"]["raw_data_path"]
    interim_data_path = config["data"]["interim_data_path"]
    validation_report_path = config["data"]["validation_report_path"]

    required_columns = config["schema"]["required_columns"]
    numeric_columns = config["schema"]["numeric_columns"]
    target_column = config["target"]["name"]

    drop_duplicates = bool(config["preprocessing"]["drop_duplicates"])

    logger.info("Starting dataset creation pipeline.")

    raw_dataframe = load_paysim_csv(raw_data_path)

    validation_report = create_validation_report(
        dataframe=raw_dataframe,
        required_columns=required_columns,
        numeric_columns=numeric_columns,
        target_column=target_column,
    )

    save_validation_report(
        report=validation_report,
        output_path=validation_report_path,
    )

    assert_valid_dataset(validation_report)

    cleaned_dataframe = clean_paysim_data(
        dataframe=raw_dataframe,
        drop_duplicates=drop_duplicates,
    )

    save_cleaned_data(
        dataframe=cleaned_dataframe,
        output_path=interim_data_path,
    )

    logger.info("Dataset creation pipeline completed successfully.")


if __name__ == "__main__":
    main()