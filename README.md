# FraudDetectAI — AI-Based Fraud Detection in Banking Transaction Database

A Database Systems course project: relational banking transactions, ACID transfers,
concurrency protection, SQL triggers/audit logs, indexed analytics and integrated
PaySim fraud detection. The existing ML pipeline and analysis pages are preserved.

## Local setup

Python 3.13 is tested. From this directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH=src:.
cp .env.example .env  # only if you do not already have .env
```

A fitted **baseline** model is required for transfers. If one already exists, set
`MODEL_PATH` to it. With the real PaySim CSV at
`data/raw/PS_20174392719_1491204439457_log.csv`, generate a bounded local artifact:

```bash
python scripts/train_banking_model.py
```

This calls the existing Random Forest pipeline on real labeled rows. It records
sample-selection limitations and evaluation in `reports/metrics/banking_model_metadata.json`.
It is an integration model, not a claim of calibrated production accuracy. Use the
original pipeline below for full research training. Model/data files are gitignored;
clones must provide the PaySim dataset or a compatible trusted joblib artifact.

### Recommended PostgreSQL setup

```bash
docker compose up -d postgres
export DATABASE_URL='postgresql+psycopg://frauddetect:local_demo_password@localhost:5432/frauddetect'
alembic upgrade head
python scripts/seed_database.py
uvicorn app.main:app --reload
```

The password is a local-demo default. Set `POSTGRES_PASSWORD` before first container
creation if desired, then update the URL. PostgreSQL data persists in a named volume.
`docker compose up --build -d` optionally runs the backend too; generate/provide the
baseline model first because the container mounts `./models` read-only. Apply seed
scripts from your host with the PostgreSQL URL. Ports bind to localhost.

### Zero-server SQLite fallback

```bash
export DATABASE_URL=sqlite:///data/banking.db
alembic upgrade head
python scripts/seed_database.py
uvicorn app.main:app --reload
```

SQLite uses real foreign keys, constraints, alert/audit triggers, views, persistence
and database writer locking. **PostgreSQL is required for the full row-locking,
JSONB and stored-function demonstration.** The UI reports the active dialect.

In a second terminal:

```bash
source .venv/bin/activate
export PYTHONPATH=src:.
streamlit run app/streamlit_app.py
```

Open [the dashboard](http://localhost:8501) and [API documentation](http://localhost:8000/docs).
Banking includes registration, transfers, filters, alert reviews and customer profiles.
DBMS Demonstration exposes live objects, audits, query plans, rollback and concurrency.
Original ML pages still use their batch-generated artifacts.

## Configuration

`.env.example` includes `DATABASE_URL`, `MODEL_PATH`, `FRAUD_THRESHOLD`, `APP_ENV` and
`BANKING_API_URL`. The threshold initializes the database singleton on migration;
update `risk_settings` via SQL to change it afterward. Keep `.env` uncommitted.
`APP_ENV=production` omits development demo routes. Authentication is optional and
not implemented; this course application is intended to run locally.

## Transfer workflow

```text
Validated request → lock customer and both accounts → debit/credit and store transfer
→ indexed SQL history → existing baseline model → store probability and behaviour risk
→ database alert/audit triggers → commit → dashboard
```

Any essential failure rolls back all writes. Monetary values use Decimal/NUMERIC.
Same-currency internal transfers are supported; external payment/cash/deposit balance
semantics are deliberately not inferred. Device/location fields are application/demo
metadata, not fabricated PaySim attributes. Final risk is a documented heuristic;
the original ML probability is separately stored and displayed.

Example request after seeding:

```bash
curl -X POST http://localhost:8000/transactions \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"C001","account_id":"A001","destination_account_id":"A002","amount":"4500.00","payment_method":"UPI","device_id":"D001","location":"Vellore"}'
```

## Tests and demonstrations

```bash
python -m pytest -q
# Also exercise PostgreSQL migrations, triggers, SQL functions and actual row locks:
TEST_DATABASE_URL="$DATABASE_URL" python -m pytest tests/test_banking.py -q
python scripts/demo_fraud.py
python scripts/demo_rollback.py
python scripts/demo_concurrency.py
docker compose exec -T postgres psql -U frauddetect -d frauddetect < docs/dbms_demo.sql
```

PostgreSQL tests use isolated disposable schemas. The seed creates 20 customers,
30 accounts, 22 devices and 426 model-scored synthetic banking transfers. ACID demos
use disposable accounts and retain redacted audit history. Fraud demos intentionally
add persisted transactions; repeated runs affect historical risk.

## Architecture and academic documentation

- [Architecture and repository audit](docs/ARCHITECTURE.md)
- [Database design, ER diagram and normalization tradeoffs](docs/DATABASE_DESIGN.md)
- [DBMS concepts and implementation examples](docs/DBMS_CONCEPTS.md)
- [5–10 minute viva guide](docs/DEMO_GUIDE.md)
- [Executable PostgreSQL demonstrations](docs/dbms_demo.sql)

Screenshots to capture: Banking overview, stored prediction, trigger alert,
old/new audit values, query plan, concurrency result and rollback result.

---

## Existing ML pipeline reference

# FraudDetect AI: Graph-Based Financial Fraud Detection

FraudDetect AI is a machine learning project that detects suspicious financial transactions by combining traditional transaction-level features with graph-based account-network features.

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

FraudDetect AI addresses this by combining:

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

FraudDetect AI creates graph features in three categories.

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

FraudDetect AI includes:

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
