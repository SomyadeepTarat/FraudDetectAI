# 5–10 minute university demonstration

## Preparation

From the project root, activate `.venv`, install requirements, then:

```bash
export PYTHONPATH=src:.
python scripts/train_banking_model.py  # only when no baseline artifact exists
# PostgreSQL is the recommended viva database:
docker compose up -d postgres
export DATABASE_URL='postgresql+psycopg://frauddetect:local_demo_password@localhost:5432/frauddetect'
alembic upgrade head
python scripts/seed_database.py
uvicorn app.main:app --reload
```

In a second terminal use the same virtual environment and `PYTHONPATH=src:.`:

```bash
streamlit run app/streamlit_app.py
```

The API is at http://localhost:8000/docs and Streamlit at http://localhost:8501.
If the PostgreSQL password/port was customized, adjust the URL. Synthetic banking
seed data uses 20 customers, 30 accounts, 22 devices and 426 real model-scored
transfers. Device/location/transfer patterns are simulated application metadata;
the model was trained on real PaySim rows. Seeding skips a nonempty customer table.

## Demonstration order

1. **Schema (1 min):** Open DBMS Demonstration. Show the live tables, keys (ER diagram
   in `DATABASE_DESIGN.md`), indexes, database triggers, SQL views and stored functions.
2. **Normal transfer (1 min):** Banking → Transfer: C001, A001 → A002, ₹4,500,
   device D001, Vellore. Show the resulting transaction ID, balances, stored ML
   probability, rule score, final risk and historical counters. At a normal UTC hour
   on a fresh seeded database the rule score is low; predictions are never hard-coded.
3. **Suspicious pattern (1 min):** Execute:
   `python scripts/demo_fraud.py`. This creates normal, new-device, ₹85,000/new-location
   and 25-payment burst scenarios. Compare the ML probability to the behaviour risk;
   not every high amount alone must fool a model trained on balance inconsistencies.
   At 20 payments within ten minutes the velocity rule alone reaches alert risk.
4. **Alert trigger (30 s):** Open Fraud alerts. The prediction INSERT caused the
   database trigger to create an OPEN alert. There is no Python INSERT into alerts
   in the transfer service. Review the persisted reasons and scores.
5. **Audit (1 min):** Change an alert to INVESTIGATING with your reviewer name.
   Open Audit trail, select fraud_alerts and inspect old/new JSON values.
6. **Query/index (1 min):** DBMS → Measure query plan for C001. Explain the customer/time
   filter and composite index; PostgreSQL may reasonably choose a sequential scan
   on this small demo dataset. Use the SQL file for EXPLAIN ANALYZE during evaluation.
7. **Concurrency (1 min):** Click the concurrency button or run
   `python scripts/demo_concurrency.py`. Two independent simultaneous debits of ₹8,000
   and ₹7,000 compete for ₹10,000. Show one success, one rejection and conserved balances.
8. **Rollback (1 min):** Click rollback or run `python scripts/demo_rollback.py`.
   Show insufficient balance rejection and intentional inference failure after writes;
   before/after balances, row counts and relevant audit counts must match.
9. **Analytics (30 s):** Show overview, customer profile and suspicious SQL view.
   Distinguish model-classified FRAUD from reviewed/resolved alerts.
10. **SQL (optional):** Run examples from `docs/dbms_demo.sql` against PostgreSQL.
    Demonstrate joins, GROUP BY/HAVING, a nested query and stored function calls.

Demo scripts create disposable ACID/concurrency rows and clean them afterward;
redacted audit entries remain as evidence. They do not modify the existing customer's
balances. The fraud script intentionally commits additional demo transactions to
C001's history; rerunning it changes historical statistics and may classify its
"normal" transaction as suspicious following an earlier burst. Start with a fresh
course demo database if you need a pristine narrative; never drop your working data
merely to repeat the demonstration.

## Verification

```bash
python -m pytest -q
TEST_DATABASE_URL="$DATABASE_URL" python -m pytest tests/test_banking.py -q
```

The second command exercises PostgreSQL and SQLite; PostgreSQL cases use new
isolated schemas per test and drop only those schemas. Do not pass a database user
without permission to create schemas. Test probability stubs are confined to unit
and integration fixtures; application and seed/demo predictions use the real artifact.

Production mode omits `/demo/*`; use CLI demonstrations locally. Authentication is
optional in this course project, so keep the server on localhost.

## Screenshot checklist

Capture Banking overview, one prediction detail, OPEN alerts, old/new audit JSON,
DBMS schema metadata, a measured query plan, concurrency output and rollback output.
