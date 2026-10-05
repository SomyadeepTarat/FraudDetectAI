"""Live database-backed banking UI, alongside the existing ML exploration pages."""

from datetime import datetime, time, timezone

import pandas as pd
import streamlit as st

from app.banking_client import api

st.set_page_config(page_title="Banking | FraudDetectAI", page_icon="🏦", layout="wide")
st.title("FraudDetectAI · Banking database")
st.caption(
    "Atomic transfers, real model inference, persisted alerts and customer history. Device/location metadata is application data, absent from PaySim."
)

stats = api("GET", "/fraud/statistics")
if stats is None:
    st.stop()
metrics = [
    ("Transactions", "total_transactions"),
    ("Amount", "total_transaction_amount"),
    ("Suspicious", "suspicious_transactions"),
    ("Resolved fraud", "confirmed_fraud_transactions"),
    ("Open alerts", "open_alerts"),
    ("Average risk", "average_fraud_risk"),
]
for start in (0, 3):
    for column, (label, key) in zip(st.columns(3), metrics[start : start + 3]):
        value = float(stats[key])
        if key == "average_fraud_risk":
            display = f"{value:.1%}"
        elif key == "total_transaction_amount":
            display = (
                f"{value / 1_000_000:.2f}M"
                if value >= 1_000_000
                else f"{value / 1_000:.2f}K"
                if value >= 1_000
                else f"{value:.2f}"
            )
        else:
            display = f"{int(value):,}"
        column.metric(label, display)
st.caption(
    "Resolved fraud counts reviewed alerts marked RESOLVED; the ML's FRAUD classification alone is not confirmation."
)
customers = api("GET", "/customers", params={"limit": 1000}) or []
accounts = api("GET", "/accounts", params={"limit": 1000}) or []
devices = api("GET", "/devices", params={"limit": 1000}) or []

overview, create, history, alerts_tab, profile, manage = st.tabs(
    [
        "Overview",
        "Transfer",
        "Transactions",
        "Fraud alerts",
        "Customer profile",
        "Register",
    ]
)
with overview:
    st.subheader("Suspicious transactions · SQL view")
    rows = api("GET", "/fraud/suspicious-transactions") or []
    st.dataframe(pd.DataFrame(rows), width="stretch")
    st.metric("Model-classified fraud", stats["model_classified_fraud"])
with create:
    if not customers or len(accounts) < 2:
        st.info(
            "Run `python scripts/seed_database.py` or register customers and accounts."
        )
    else:
        customer_id = st.selectbox(
            "Customer", [c["customer_id"] for c in customers], key="transfer_customer"
        )
        own_accounts = [
            a["account_id"] for a in accounts if a["customer_id"] == customer_id
        ]
        own_devices = [
            d["device_id"] for d in devices if d["customer_id"] == customer_id
        ]
        if own_accounts:
            with st.form("transfer"):
                source = st.selectbox("Source account", own_accounts)
                destination = st.selectbox(
                    "Destination account", [a["account_id"] for a in accounts]
                )
                amount = st.text_input("Amount (two decimal places)", "4500.00")
                method = st.selectbox(
                    "Payment method", ["UPI", "NEFT", "IMPS", "CARD", "BANK"]
                )
                device = st.selectbox("Registered device", [None] + own_devices)
                location = st.text_input("Application location", "Vellore")
                submit = st.form_submit_button("Process transfer")
            if submit:
                result = api(
                    "POST",
                    "/transactions",
                    json={
                        "customer_id": customer_id,
                        "account_id": source,
                        "destination_account_id": destination,
                        "amount": amount,
                        "payment_method": method,
                        "device_id": device,
                        "location": location or None,
                    },
                )
                if result:
                    st.success(
                        f"Committed {result['transaction_id']} · {result['prediction']['classification']}"
                    )
                    st.json(result)
                    st.session_state["latest_transfer"] = result
        else:
            st.info("Register an account for this customer.")
with history:
    col1, col2, col3 = st.columns(3)
    customer_filter = col1.selectbox(
        "Customer filter", [""] + [c["customer_id"] for c in customers]
    )
    suspicious = col2.checkbox("Suspicious only")
    risk = col3.slider("Minimum risk", 0.0, 1.0, 0.0)
    col1, col2, col3 = st.columns(3)
    min_amount = col1.number_input("Minimum amount", min_value=0.0)
    start = col2.date_input("From (UTC)", value=None)
    end = col3.date_input("Until (UTC)", value=None)
    params = {"suspicious_only": suspicious, "min_risk": risk, "min_amount": min_amount}
    if customer_filter:
        params["customer_id"] = customer_filter
    if start:
        params["since"] = datetime.combine(
            start, time.min, tzinfo=timezone.utc
        ).isoformat()
    if end:
        params["until"] = datetime.combine(
            end, time.max, tzinfo=timezone.utc
        ).isoformat()
    rows = api("GET", "/transactions", params=params) or []
    table = [
        {k: v for k, v in row.items() if k != "prediction"}
        | {
            "fraud_probability": (row.get("prediction") or {}).get("fraud_probability"),
            "risk_score": (row.get("prediction") or {}).get("risk_score"),
            "classification": (row.get("prediction") or {}).get("classification"),
        }
        for row in rows
    ]
    st.dataframe(pd.DataFrame(table), width="stretch")
    if rows:
        selected = st.selectbox(
            "Inspect transaction and prediction", [r["transaction_id"] for r in rows]
        )
        st.json(next(row for row in rows if row["transaction_id"] == selected))
with alerts_tab:
    status_filter = st.selectbox(
        "Alert status filter",
        ["", "OPEN", "INVESTIGATING", "RESOLVED", "FALSE_POSITIVE"],
    )
    alert_rows = (
        api(
            "GET",
            "/fraud/alerts",
            params={"status": status_filter} if status_filter else {},
        )
        or []
    )
    st.dataframe(pd.DataFrame(alert_rows), width="stretch")
    if alert_rows:
        with st.form("review_alert"):
            alert_id = st.selectbox(
                "Alert to review", [a["alert_id"] for a in alert_rows]
            )
            state = st.selectbox(
                "New status", ["INVESTIGATING", "RESOLVED", "FALSE_POSITIVE", "OPEN"]
            )
            actor = st.text_input("Reviewer", "university-demo")
            review = st.form_submit_button("Save review")
        if review:
            result = api(
                "PATCH",
                f"/fraud/alerts/{alert_id}",
                json={"alert_status": state, "reviewed_by": actor},
            )
            if result:
                st.success("Review saved; audit trigger recorded the change.")
                st.json(result)
with profile:
    if customers:
        customer_id = st.selectbox(
            "Profile customer", [c["customer_id"] for c in customers]
        )
        summary = api("GET", f"/customers/{customer_id}/risk-summary")
        st.json(summary)
        st.dataframe(
            pd.DataFrame(api("GET", f"/customers/{customer_id}/transactions") or []),
            width="stretch",
        )
        state = st.selectbox("Customer status", ["ACTIVE", "UNDER_REVIEW", "BLOCKED"])
        if st.button("Update customer status") and api(
            "PATCH", f"/customers/{customer_id}", json={"status": state}
        ):
            st.success("Customer status saved and audited.")
with manage:
    with st.form("register_customer"):
        st.subheader("Customer")
        name = st.text_input("Name")
        email = st.text_input("Email")
        if st.form_submit_button("Register customer"):
            result = api("POST", "/customers", json={"name": name, "email": email})
            if result:
                st.json(result)
    if customers:
        with st.form("register_account"):
            st.subheader("Account")
            owner = st.selectbox("Account owner", [c["customer_id"] for c in customers])
            balance = st.text_input("Opening balance", "10000.00")
            if st.form_submit_button("Open account"):
                result = api(
                    "POST", "/accounts", json={"customer_id": owner, "balance": balance}
                )
                if result:
                    st.json(result)
        with st.form("register_device"):
            st.subheader("Device")
            owner = st.selectbox("Device owner", [c["customer_id"] for c in customers])
            identifier = st.text_input("Unique device identifier")
            trusted = st.checkbox("Trusted device")
            if st.form_submit_button("Register device"):
                result = api(
                    "POST",
                    "/devices",
                    json={
                        "customer_id": owner,
                        "device_identifier": identifier,
                        "trusted": trusted,
                    },
                )
                if result:
                    st.json(result)
