import streamlit as st

from dashboard_utils import (
    file_exists,
    filter_transactions,
    get_available_columns,
    load_parquet_file,
)


st.set_page_config(
    page_title="Fraud Detection | FraudGraph AI",
    page_icon="🚨",
    layout="wide",
)

st.title(" Fraud Detection")

scored_transactions_path = "data/processed/scored_transactions.parquet"

if not file_exists(scored_transactions_path):
    st.error("Scored transactions file not found. Run `python scripts/tune_threshold.py` first.")
    st.stop()

scored_dataframe = load_parquet_file(scored_transactions_path)

st.sidebar.header("Filters")

available_risk_bands = sorted(scored_dataframe["risk_band"].dropna().unique().tolist())

selected_risk_bands = st.sidebar.multiselect(
    "Risk Bands",
    options=available_risk_bands,
    default=available_risk_bands,
)

predicted_fraud_only = st.sidebar.checkbox(
    "Show predicted fraud only",
    value=False,
)

min_probability = st.sidebar.slider(
    "Minimum fraud probability",
    min_value=0.0,
    max_value=1.0,
    value=0.0,
    step=0.01,
)

max_rows = st.sidebar.slider(
    "Rows to show",
    min_value=10,
    max_value=1000,
    value=100,
    step=10,
)

filtered_dataframe = filter_transactions(
    dataframe=scored_dataframe,
    risk_bands=selected_risk_bands,
    predicted_fraud_only=predicted_fraud_only,
    min_probability=min_probability,
    max_rows=max_rows,
)

st.write(f"Showing **{len(filtered_dataframe)}** transactions.")

preferred_columns = [
    "nameOrig",
    "nameDest",
    "type",
    "amount",
    "fraud_probability",
    "predicted_fraud",
    "risk_band",
    "isFraud",
    "oldbalanceOrg",
    "newbalanceOrig",
    "origin_balance_delta",
    "amount_to_old_origin_balance_ratio",
    "sender_out_degree",
    "receiver_in_degree",
    "receiver_incoming_fraud_rate",
    "sender_receiver_edge_fraud_rate",
]

display_columns = get_available_columns(
    dataframe=filtered_dataframe,
    preferred_columns=preferred_columns,
)

st.dataframe(
    filtered_dataframe[display_columns],
    use_container_width=True,
)

st.divider()

st.subheader("Top Risky Transactions")

top_n = st.slider(
    "Top N transactions",
    min_value=5,
    max_value=100,
    value=20,
    step=5,
)

top_risky = scored_dataframe.sort_values(
    by="fraud_probability",
    ascending=False,
).head(top_n)

top_display_columns = get_available_columns(
    dataframe=top_risky,
    preferred_columns=preferred_columns,
)

st.dataframe(
    top_risky[top_display_columns],
    use_container_width=True,
)