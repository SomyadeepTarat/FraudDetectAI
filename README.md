# FraudGraph AI: Graph-Based Financial Fraud Detection

FraudGraph AI is a machine learning project that detects suspicious financial transactions by combining traditional transaction-level features with graph-based account-network features.

Instead of treating every transaction as an isolated row, this project models the financial ecosystem as a directed sender-receiver graph:

```text
sender_account → receiver_account
```

This allows the model to learn not only transaction behavior, but also relational fraud patterns such as high-risk receivers, suspicious sender-receiver relationships, account-draining behavior, and fraud-heavy transaction neighborhoods.

---

## Project Highlights

* Built a complete fraud detection pipeline from raw transaction data to dashboard.
* Modeled transactions as a directed graph using NetworkX.
* Engineered sender, receiver, and sender-receiver edge features.
* Trained transaction-only baseline models and graph-enhanced models.
* Compared Logistic Regression, Random Forest, and XGBoost.
* Evaluated models using fraud-specific metrics such as precision, recall, F1, ROC-AUC, and average precision.
* Tuned probability thresholds for fraud risk scoring.
* Created LOW, MEDIUM, HIGH, and CRITICAL risk bands.
* Added global feature importance and transaction-level explanations.
* Built a Streamlit dashboard for fraud investigation.

---

## Problem Statement

Fraud detection is difficult because fraudulent transactions are rare and often hidden among millions of legitimate transactions.

Traditional fraud classifiers usually look at each transaction independently. However, fraud is often relational. A transaction may appear normal on its own but suspicious when viewed through the account network.

FraudGraph AI addresses this by combining:

1. Transaction-level ML features
2. Graph-based account behavior features
3. Risk scoring and explainability
4. An interactive fraud investigation dashboard

---

## Dataset

This project is designed around the PaySim mobile money fraud dataset.

Expected raw data path:

```text
data/raw/PS_20174392719_1491204439457_log.csv
```

The dataset includes columns such as:

```text
step
type
amount
nameOrig
oldbalanceOrg
newbalanceOrig
nameDest
oldbalanceDest
newbalanceDest
isFraud
isFlaggedFraud
```

The raw dataset is not committed to GitHub. Place it manually inside `data/raw/`.

---

## Project Architecture

```text
fraudgraph-ai/
│
├── app/
│   ├── streamlit_app.py
│   ├── dashboard_utils.py
│   └── pages/
│       ├── 1_Overview.py
│       ├── 2_Fraud_Detection.py
│       ├── 3_Graph_Explorer.py
│       ├── 4_Model_Performance.py
│       └── 5_Explainability.py
│
├── configs/
│   └── config.yaml
│
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   └── external/
│
├── models/
│   ├── baseline/
│   ├── graph_enhanced/
│   └── artifacts/
│
├── notebooks/
│   ├── 01_data_understanding.ipynb
│   ├── 02_baseline_modeling.ipynb
│   ├── 03_graph_feature_exploration.ipynb
│   └── 04_model_evaluation.ipynb
│
├── reports/
│   ├── figures/
│   ├── metrics/
│   └── model_cards/
│
├── scripts/
│   ├── make_dataset.py
│   ├── run_eda.py
│   ├── train_baseline.py
│   ├── build_transaction_graph.py
│   ├── create_graph_features.py
│   ├── train_graph_model.py
│   ├── tune_threshold.py
│   ├── explain_model.py
│   ├── run_app.py
│   └── run_full_pipeline.py
│
├── src/
│   └── fraudgraph/
│       ├── data/
│       ├── eda/
│       ├── explainability/
│       ├── features/
│       ├── graph/
│       ├── models/
│       └── utils/
│
├── tests/
│
├── .env.example
├── .gitignore
├── Makefile
├── MODEL_CARD.md
├── PROJECT_REPORT.md
├── README.md
├── pyproject.toml
└── requirements.txt
```

---

## Machine Learning Workflow

```text
Raw PaySim CSV
      ↓
Data validation
      ↓
Preprocessing and transaction features
      ↓
EDA and fraud behavior analysis
      ↓
Transaction-only baseline models
      ↓
Directed transaction graph construction
      ↓
Graph feature engineering
      ↓
Graph-enhanced model training
      ↓
Baseline vs graph comparison
      ↓
Threshold tuning
      ↓
Risk scoring
      ↓
Explainability
      ↓
Streamlit dashboard
```

---

## Models

The project trains the following model families:

1. Logistic Regression
2. Random Forest
3. XGBoost

Each model is trained in two settings:

```text
transaction-only baseline
transaction + graph-enhanced features
```

This allows a clear comparison of how graph features affect fraud detection performance.

---

## Graph Features

FraudGraph AI creates graph features in three categories.

### Sender Features

```text
sender_in_degree
sender_out_degree
sender_total_degree
sender_total_sent_amount
sender_total_received_amount
sender_outgoing_transaction_count
sender_incoming_transaction_count
sender_outgoing_fraud_rate
sender_incoming_fraud_rate
sender_avg_sent_amount
sender_avg_received_amount
```

### Receiver Features

```text
receiver_in_degree
receiver_out_degree
receiver_total_degree
receiver_total_sent_amount
receiver_total_received_amount
receiver_outgoing_transaction_count
receiver_incoming_transaction_count
receiver_outgoing_fraud_rate
receiver_incoming_fraud_rate
receiver_avg_sent_amount
receiver_avg_received_amount
```

### Sender-Receiver Edge Features

```text
sender_receiver_edge_transaction_count
sender_receiver_edge_total_amount
sender_receiver_edge_avg_amount
sender_receiver_edge_fraud_count
sender_receiver_edge_fraud_rate
```

---

## Evaluation Metrics

Because fraud detection is highly imbalanced, accuracy alone is not enough.

This project evaluates models using:

```text
accuracy
precision
recall
F1 score
ROC-AUC
average precision
confusion matrix
```

The most important metrics are:

```text
recall
precision
F1
average precision
```

Average precision is especially useful because it evaluates how well the model ranks rare fraud cases near the top.

---

## Setup Instructions

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
pip install -e .
```

Copy environment file:

```bash
cp .env.example .env
```

Place the PaySim CSV file in:

```text
data/raw/PS_20174392719_1491204439457_log.csv
```

---

## Run the Full Pipeline

Run all steps:

```bash
python scripts/run_full_pipeline.py
```

Or run each step manually:

```bash
python scripts/make_dataset.py
python scripts/run_eda.py
python scripts/train_baseline.py
python scripts/build_transaction_graph.py
python scripts/create_graph_features.py
python scripts/train_graph_model.py
python scripts/tune_threshold.py
python scripts/explain_model.py
```

---

## Launch Dashboard

```bash
streamlit run app/streamlit_app.py
```

or:

```bash
python scripts/run_app.py
```

---

## Run Tests

```bash
pytest
```

---

## Dashboard Pages

The Streamlit dashboard includes:

1. Overview
2. Fraud Detection
3. Graph Explorer
4. Model Performance
5. Explainability

The dashboard allows users to:

* inspect scored transactions
* filter by risk band
* compare baseline vs graph models
* view graph summary statistics
* inspect threshold tuning
* review transaction explanations

---

## Explainability

FraudGraph AI includes:

1. Global feature importance
2. Transaction-level rule explanations

Example explanation:

```text
Transaction flagged as CRITICAL because:
- Model assigned a high fraud probability.
- Transaction type is TRANSFER.
- Sender's balance was emptied after the transaction.
- Receiver has a high incoming fraud rate.
- Sender-receiver relationship has previous fraud signal.
```

---

## Important Limitation: Graph Leakage

The current graph feature pipeline may use full-graph aggregate statistics. Some features, such as receiver fraud rate or sender-receiver edge fraud rate, may include information from the same transaction or future transactions.

This is acceptable for learning and demonstrating graph-based fraud signals, but a production-safe system should compute graph features using only historical transactions or only the training graph.

A future production version should implement time-aware graph feature generation.

---

## Future Improvements

* Time-aware graph feature generation to prevent leakage
* SHAP explanations for local prediction interpretability
* Graph Neural Network extension using GraphSAGE or GCN
* FastAPI fraud scoring endpoint
* MLflow experiment tracking
* Dockerized deployment
* Drift monitoring
* Database-backed transaction storage
* Analyst feedback loop for fraud investigation outcomes

---

## Resume Summary

FraudGraph AI is a graph-based fraud detection system that models sender-receiver transaction networks and uses graph-enhanced machine learning to identify suspicious transactions. The project includes end-to-end data processing, graph feature engineering, baseline comparison, model evaluation, threshold tuning, explainability, and a Streamlit investigation dashboard.
