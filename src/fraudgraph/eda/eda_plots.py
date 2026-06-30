from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from fraudgraph.utils.logger import get_logger
from fraudgraph.utils.paths import ensure_dir

logger = get_logger(__name__)


def sample_dataframe_for_plotting(
    dataframe: pd.DataFrame,
    sample_size: int,
    random_seed: int,
) -> pd.DataFrame:
    
    if sample_size <= 0:
        raise ValueError("sample_size must be greater than 0.")

    if len(dataframe) <= sample_size:
        return dataframe.copy()

    return dataframe.sample(n=sample_size, random_state=random_seed).copy()


def save_class_distribution_plot(
    dataframe: pd.DataFrame,
    target_column: str,
    output_dir: str | Path,
) -> Path:

    resolved_output_dir = ensure_dir(output_dir)
    output_path = resolved_output_dir / "class_distribution.png"

    counts = dataframe[target_column].value_counts().sort_index()

    plt.figure(figsize=(8, 5))
    plt.bar(counts.index.astype(str), counts.to_numpy())
    plt.title("Class Distribution: Non-Fraud vs Fraud")
    plt.xlabel("Class")
    plt.ylabel("Number of Transactions")
    plt.xticks(ticks=[0, 1], labels=["Non-Fraud", "Fraud"])
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info("Saved class distribution plot to: %s", output_path)

    return output_path


def save_transaction_type_distribution_plot(
    dataframe: pd.DataFrame,
    transaction_type_column: str,
    output_dir: str | Path,
) -> Path:

    resolved_output_dir = ensure_dir(output_dir)
    output_path = resolved_output_dir / "transaction_type_distribution.png"

    counts = dataframe[transaction_type_column].value_counts()

    plt.figure(figsize=(9, 5))
    plt.bar(counts.index.astype(str), counts.to_numpy())
    plt.title("Transaction Type Distribution")
    plt.xlabel("Transaction Type")
    plt.ylabel("Number of Transactions")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info("Saved transaction type distribution plot to: %s", output_path)

    return output_path


def save_fraud_by_transaction_type_plot(
    dataframe: pd.DataFrame,
    transaction_type_column: str,
    target_column: str,
    output_dir: str | Path,
) -> Path:

    resolved_output_dir = ensure_dir(output_dir)
    output_path = resolved_output_dir / "fraud_by_transaction_type.png"

    grouped = (
        dataframe.groupby(transaction_type_column, observed=True)[target_column]
        .mean()
        .sort_values(ascending=False)
    )

    plt.figure(figsize=(9, 5))
    plt.bar(grouped.index.astype(str), grouped.to_numpy())
    plt.title("Fraud Rate by Transaction Type")
    plt.xlabel("Transaction Type")
    plt.ylabel("Fraud Rate")
    plt.xticks(rotation=30, ha="right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info("Saved fraud by transaction type plot to: %s", output_path)

    return output_path


def save_amount_distribution_by_fraud_plot(
    dataframe: pd.DataFrame,
    target_column: str,
    output_dir: str | Path,
) -> Path:

    resolved_output_dir = ensure_dir(output_dir)
    output_path = resolved_output_dir / "amount_distribution_by_fraud.png"

    non_fraud_amount = dataframe.loc[dataframe[target_column] == 0, "amount"]
    fraud_amount = dataframe.loc[dataframe[target_column] == 1, "amount"]

    plt.figure(figsize=(9, 5))
    plt.hist(
        non_fraud_amount.clip(lower=0) + 1,
        bins=50,
        alpha=0.6,
        label="Non-Fraud",
    )
    plt.hist(
        fraud_amount.clip(lower=0) + 1,
        bins=50,
        alpha=0.6,
        label="Fraud",
    )
    plt.xscale("log")
    plt.title("Transaction Amount Distribution by Fraud Class")
    plt.xlabel("Amount + 1, log scale")
    plt.ylabel("Frequency")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info("Saved amount distribution plot to: %s", output_path)

    return output_path


def save_origin_balance_delta_by_fraud_plot(
    dataframe: pd.DataFrame,
    target_column: str,
    output_dir: str | Path,
) -> Path:

    resolved_output_dir = ensure_dir(output_dir)
    output_path = resolved_output_dir / "origin_balance_delta_by_fraud.png"

    non_fraud_delta = dataframe.loc[
        dataframe[target_column] == 0,
        "origin_balance_delta",
    ]
    fraud_delta = dataframe.loc[
        dataframe[target_column] == 1,
        "origin_balance_delta",
    ]

    plt.figure(figsize=(9, 5))
    plt.hist(non_fraud_delta.clip(lower=0) + 1, bins=50, alpha=0.6, label="Non-Fraud")
    plt.hist(fraud_delta.clip(lower=0) + 1, bins=50, alpha=0.6, label="Fraud")
    plt.xscale("log")
    plt.title("Origin Balance Delta Distribution by Fraud Class")
    plt.xlabel("Origin Balance Delta + 1, log scale")
    plt.ylabel("Frequency")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info("Saved origin balance delta plot to: %s", output_path)

    return output_path


def save_amount_ratio_by_fraud_plot(
    dataframe: pd.DataFrame,
    target_column: str,
    output_dir: str | Path,
) -> Path:

    resolved_output_dir = ensure_dir(output_dir)
    output_path = resolved_output_dir / "amount_ratio_by_fraud.png"

    plot_dataframe = dataframe[
        [
            target_column,
            "amount_to_old_origin_balance_ratio",
        ]
    ].copy()

    plot_dataframe["amount_to_old_origin_balance_ratio"] = plot_dataframe[
        "amount_to_old_origin_balance_ratio"
    ].replace([float("inf"), -float("inf")], pd.NA)

    plot_dataframe = plot_dataframe.dropna()
    plot_dataframe = plot_dataframe[
        plot_dataframe["amount_to_old_origin_balance_ratio"] >= 0
    ]

    non_fraud_ratio = plot_dataframe.loc[
        plot_dataframe[target_column] == 0,
        "amount_to_old_origin_balance_ratio",
    ]

    fraud_ratio = plot_dataframe.loc[
        plot_dataframe[target_column] == 1,
        "amount_to_old_origin_balance_ratio",
    ]

    upper_limit = plot_dataframe["amount_to_old_origin_balance_ratio"].quantile(0.99)

    non_fraud_ratio = non_fraud_ratio[non_fraud_ratio <= upper_limit]
    fraud_ratio = fraud_ratio[fraud_ratio <= upper_limit]

    plt.figure(figsize=(9, 5))
    plt.hist(non_fraud_ratio, bins=50, alpha=0.6, label="Non-Fraud")
    plt.hist(fraud_ratio, bins=50, alpha=0.6, label="Fraud")
    plt.title("Amount-to-Origin-Balance Ratio by Fraud Class")
    plt.xlabel("Amount / Old Origin Balance")
    plt.ylabel("Frequency")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info("Saved amount ratio plot to: %s", output_path)

    return output_path


def save_correlation_heatmap(
    dataframe: pd.DataFrame,
    target_column: str,
    output_dir: str | Path,
) -> Path:

    resolved_output_dir = ensure_dir(output_dir)
    output_path = resolved_output_dir / "correlation_heatmap.png"

    selected_columns = [
        "amount",
        "oldbalanceOrg",
        "newbalanceOrig",
        "oldbalanceDest",
        "newbalanceDest",
        "origin_balance_delta",
        "destination_balance_delta",
        "amount_to_old_origin_balance_ratio",
        "amount_to_old_destination_balance_ratio",
        "is_origin_balance_emptied",
        "is_destination_balance_unchanged",
        "is_transfer_type",
        "is_cashout_type",
        target_column,
    ]

    existing_columns = [
        column for column in selected_columns if column in dataframe.columns
    ]

    correlation_matrix = dataframe[existing_columns].corr(numeric_only=True)

    plt.figure(figsize=(12, 9))
    image = plt.imshow(correlation_matrix, aspect="auto")
    plt.colorbar(image)
    plt.xticks(
        ticks=range(len(correlation_matrix.columns)),
        labels=list(correlation_matrix.columns),
        rotation=90,
    )
    plt.yticks(
        ticks=range(len(correlation_matrix.index)),
        labels=list(correlation_matrix.index),
    )
    plt.title("Correlation Heatmap of Numeric Features")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()

    logger.info("Saved correlation heatmap to: %s", output_path)

    return output_path


def generate_all_eda_plots(
    dataframe: pd.DataFrame,
    target_column: str,
    transaction_type_column: str,
    output_dir: str | Path,
    sample_size: int,
    random_seed: int,
) -> list[Path]:

    sampled_dataframe = sample_dataframe_for_plotting(
        dataframe=dataframe,
        sample_size=sample_size,
        random_seed=random_seed,
    )

    saved_paths = [
        save_class_distribution_plot(
            dataframe=dataframe,
            target_column=target_column,
            output_dir=output_dir,
        ),
        save_transaction_type_distribution_plot(
            dataframe=dataframe,
            transaction_type_column=transaction_type_column,
            output_dir=output_dir,
        ),
        save_fraud_by_transaction_type_plot(
            dataframe=dataframe,
            transaction_type_column=transaction_type_column,
            target_column=target_column,
            output_dir=output_dir,
        ),
        save_amount_distribution_by_fraud_plot(
            dataframe=sampled_dataframe,
            target_column=target_column,
            output_dir=output_dir,
        ),
        save_origin_balance_delta_by_fraud_plot(
            dataframe=sampled_dataframe,
            target_column=target_column,
            output_dir=output_dir,
        ),
        save_amount_ratio_by_fraud_plot(
            dataframe=sampled_dataframe,
            target_column=target_column,
            output_dir=output_dir,
        ),
        save_correlation_heatmap(
            dataframe=sampled_dataframe,
            target_column=target_column,
            output_dir=output_dir,
        ),
    ]

    return saved_paths