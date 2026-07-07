import pandas as pd
import streamlit as st

from dashboard_utils import (
    file_exists,
    format_number,
    format_percentage,
    load_json_file,
    load_parquet_file,
    summarize_scored_transactions,
)


st.set_page_config(
    page_title="Overview | FraudGraph AI",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Overview")

scored_transactions_path = "data/processed/scored_transactions.parquet"
eda_summary_path = "reports/metrics/eda_summary.json"
risk_report_path = "reports/metrics/final_risk_scoring_report.json"

if not file_exists(scored_transactions_path):
    st.error("Scored transactions file not found. Run `python scripts/tune_threshold.py` first.")
    st.stop()

scored_dataframe = load_parquet_file(scored_transactions_path)
summary = summarize_scored_transactions(scored_dataframe)

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Transactions Scored", format_number(summary["num_transactions"]))

with col2:
    st.metric("Predicted Fraud", format_number(summary["num_predicted_fraud"]))

with col3:
    st.metric(
        "Average Fraud Probability",
        format_percentage(summary["average_fraud_probability"]),
    )

with col4:
    st.metric(
        "Maximum Fraud Probability",
        format_percentage(summary["max_fraud_probability"]),
    )

st.divider()

left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Risk Band Counts")
    risk_band_counts = pd.DataFrame(
        {
            "risk_band": list(summary["risk_band_counts"].keys()),
            "count": list(summary["risk_band_counts"].values()),
        }
    )

    if risk_band_counts.empty:
        st.info("No risk band data available.")
    else:
        st.dataframe(risk_band_counts, use_container_width=True)
        st.bar_chart(risk_band_counts.set_index("risk_band"))

with right_col:
    st.subheader("Risk Report")

    if file_exists(risk_report_path):
        risk_report = load_json_file(risk_report_path)

        st.write(
            f"Decision threshold: **{risk_report.get('decision_threshold', 'N/A')}**"
        )

        actual_fraud_rate_by_band = risk_report.get(
            "actual_fraud_rate_by_risk_band",
            {},
        )

        if actual_fraud_rate_by_band:
            band_rate_dataframe = pd.DataFrame(
                {
                    "risk_band": list(actual_fraud_rate_by_band.keys()),
                    "actual_fraud_rate": list(actual_fraud_rate_by_band.values()),
                }
            )
            st.dataframe(band_rate_dataframe, use_container_width=True)
        else:
            st.info("No actual fraud rate by risk band available.")
    else:
        st.warning("Risk report not found.")

st.divider()

st.subheader("Original Dataset EDA Summary")

if file_exists(eda_summary_path):
    eda_summary = load_json_file(eda_summary_path)

    dataset_shape = eda_summary.get("dataset_shape", {})
    class_distribution = eda_summary.get("class_distribution", {})

    col_a, col_b, col_c = st.columns(3)

    with col_a:
        st.metric("EDA Rows", format_number(dataset_shape.get("num_rows")))

    with col_b:
        st.metric("EDA Columns", format_number(dataset_shape.get("num_columns")))

    with col_c:
        percentages = class_distribution.get("percentages", {})
        fraud_rate = percentages.get("1")
        st.metric("Actual Fraud Rate", format_percentage(fraud_rate))

    transaction_type_summary = eda_summary.get("transaction_type_summary", {})

    if transaction_type_summary:
        transaction_rows = []

        for transaction_type, values in transaction_type_summary.items():
            transaction_rows.append(
                {
                    "transaction_type": transaction_type,
                    "total_transactions": values.get("total_transactions"),
                    "fraud_transactions": values.get("fraud_transactions"),
                    "fraud_rate": values.get("fraud_rate"),
                }
            )

        transaction_summary_dataframe = pd.DataFrame(transaction_rows)
        st.dataframe(transaction_summary_dataframe, use_container_width=True)
else:
    st.warning("EDA summary not found. Run `python scripts/run_eda.py` first.")