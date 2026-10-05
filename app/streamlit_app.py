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
    page_title="FraudDetectAI",
    layout="wide",
)

st.title("FraudDetectAI")
st.subheader("AI-Based Fraud Detection in Banking Transaction Database")
st.info("Open Banking for live transfers, customer profiles and alerts, or DBMS Demonstration for schema, audit trails, rollback, concurrency and query plans. Existing ML analysis pages remain available below.")

st.markdown(
    """
FraudDetectAI processes banking transfers in a relational database with atomic
balance updates, concurrency protection, trigger-generated alerts and audit logs.
The existing PaySim model provides an integrated fraud-analysis layer.

Use the sidebar pages to explore:

- live banking transfers, alerts and customer history
- DBMS schema, audit logs, indexes, rollback and concurrency
- fraud overview
- scored transactions
- graph structure
- model performance
- transaction explanations
"""
)

st.divider()

scored_transactions_path = "data/processed/scored_transactions.parquet"
risk_report_path = "reports/metrics/final_risk_scoring_report.json"
comparison_report_path = "reports/metrics/baseline_vs_graph_comparison.json"

required_files = {
    "Scored transactions": scored_transactions_path,
    "Risk scoring report": risk_report_path,
    "Baseline vs graph comparison": comparison_report_path,
}

missing_files = [
    label
    for label, path in required_files.items()
    if not file_exists(path)
]

if missing_files:
    st.warning(
        "Some dashboard artifacts are missing. Run the full pipeline before using all dashboard pages."
    )

    st.code(
        "\n".join(
            [
                "python scripts/make_dataset.py",
                "python scripts/train_baseline.py",
                "python scripts/build_transaction_graph.py",
                "python scripts/create_graph_features.py",
                "python scripts/train_graph_model.py",
                "python scripts/tune_threshold.py",
                "python scripts/explain_model.py",
            ]
        ),
        language="bash",
    )

    st.write("Missing artifacts:")
    for missing_file in missing_files:
        st.write(f"- {missing_file}")

else:
    scored_dataframe = load_parquet_file(scored_transactions_path)
    risk_report = load_json_file(risk_report_path)
    comparison_report = load_json_file(comparison_report_path)

    scored_summary = summarize_scored_transactions(scored_dataframe)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Transactions Scored",
            format_number(scored_summary["num_transactions"]),
        )

    with col2:
        st.metric(
            "Predicted Fraud",
            format_number(scored_summary["num_predicted_fraud"]),
        )

    with col3:
        st.metric(
            "Avg Fraud Probability",
            format_percentage(scored_summary["average_fraud_probability"]),
        )

    with col4:
        st.metric(
            "Max Fraud Probability",
            format_percentage(scored_summary["max_fraud_probability"]),
        )

    st.divider()

    st.subheader("Risk Band Distribution")

    risk_band_counts = scored_summary["risk_band_counts"]

    if risk_band_counts:
        st.bar_chart(risk_band_counts)
    else:
        st.info("No risk band counts available.")

    st.subheader("Current Decision Threshold")

    st.write(
        f"Current tuned threshold: **{risk_report.get('decision_threshold', 'N/A')}**"
    )

    st.subheader("Best Model Summary")

    best_graph_model = comparison_report.get(
        "best_graph_model_by_average_precision",
        {},
    )

    st.write(
        f"Best graph-enhanced model by average precision: "
        f"**{best_graph_model.get('model_name', 'N/A')}** "
        f"with score **{best_graph_model.get('score', 'N/A')}**"
    )

st.divider()

st.caption(
    "Database Systems course project. Model predictions and synthetic banking scenarios are for academic demonstration."
)
