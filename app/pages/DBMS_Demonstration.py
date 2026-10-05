import pandas as pd
import streamlit as st

from app.banking_client import api

st.set_page_config(
    page_title="DBMS demonstration | FraudDetectAI", page_icon="🗄️", layout="wide"
)
st.title("DBMS demonstration")
metadata = api("GET", "/database/overview")
if metadata is None:
    st.stop()
st.caption(
    f"Live database: {metadata['dialect']} · Isolation: {metadata['isolation']} · Alert threshold: {metadata['threshold']}"
)
structure, audit, acid = st.tabs(
    [
        "Schema / indexes / triggers / views",
        "Audit trail",
        "ACID / concurrency / query plan",
    ]
)
with structure:
    st.json(metadata)
    st.markdown(
        "Customer → Accounts / Devices → Transactions → Fraud prediction → Fraud alert. Audit logs are written by database triggers."
    )
    st.code(
        "SELECT * FROM suspicious_transactions_view;\nSELECT * FROM customer_risk_summary;\nSELECT * FROM get_customer_transaction_stats('C001');",
        language="sql",
    )
    if metadata["dialect"] == "sqlite":
        st.info(
            "SQLite uses a database writer lock; PostgreSQL demonstrates row locks, JSONB and stored functions."
        )
with audit:
    table = st.selectbox(
        "Table",
        [
            "",
            "transactions",
            "fraud_predictions",
            "fraud_alerts",
            "accounts",
            "customers",
        ],
    )
    logs = (
        api("GET", "/audit-logs", params={"table_name": table} if table else {}) or []
    )
    st.dataframe(
        pd.DataFrame(
            [
                {k: v for k, v in row.items() if k not in ("old_values", "new_values")}
                for row in logs
            ]
        ),
        width="stretch",
    )
    if logs:
        selected = st.selectbox(
            "Inspect old and new values", [row["audit_id"] for row in logs]
        )
        st.json(next(row for row in logs if row["audit_id"] == selected))
with acid:
    st.markdown(
        "**Atomicity:** debit, credit, transaction, prediction and trigger writes commit together.\n\n**Consistency:** positive amounts, nonnegative balances, ownership and foreign keys.\n\n**Isolation:** ordered PostgreSQL row locks; SQLite `BEGIN IMMEDIATE`.\n\n**Durability:** committed rows survive restart; PostgreSQL uses the persistent Docker volume."
    )
    st.code(
        "BEGIN;\nSELECT * FROM accounts WHERE account_id IN ('A001','A002') ORDER BY account_id FOR UPDATE;\n-- Debit, credit, transaction, model prediction and trigger writes\nCOMMIT; -- ROLLBACK on failure",
        language="sql",
    )
    if st.button("Run rollback demonstration (disposable accounts)"):
        result = api("POST", "/demo/rollback")
        if result:
            st.json(result)
    if st.button("Run simultaneous ₹8,000 / ₹7,000 debits"):
        result = api("POST", "/demo/concurrency")
        if result:
            st.json(result)
    customer = st.text_input("Customer for query plan", "C001")
    if st.button("Measure query plan"):
        result = api("GET", "/demo/index-performance", params={"customer_id": customer})
        if result:
            st.json(result)
    st.caption(
        "Demo endpoints are available only when APP_ENV=development. CLI alternatives: scripts/demo_rollback.py and scripts/demo_concurrency.py."
    )
