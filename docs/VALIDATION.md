# Implementation validation — 5 October 2026

Verified locally using Python 3.13, the existing virtual environment, SQLite and a
PostgreSQL 17 Docker container. No existing ML pipeline source was replaced.

- Initial repository baseline: **88 tests passed**.
- Final full suite with `TEST_DATABASE_URL`: **127 passed, 1 skipped**.
  The skip is the PostgreSQL-only stored-function case on SQLite; the PostgreSQL
  variant passed. Dependency deprecation warnings came from Starlette/TestClient.
- Ruff checks passed for every added Python component; `git diff --check` passed.
- Alembic upgrade, downgrade to base and re-upgrade passed in disposable test
  databases/schemas, including triggers, views and stored functions.
- A real baseline artifact was trained through the existing Random Forest pipeline
  on 28,213 genuine PaySim rows (20,000 sampled normal rows plus all 8,213 fraud rows).
  Metadata records the enriched/ordered sample limitation; held-out scores are not
  evidence of calibrated real-world performance.
- Existing-model inference was exercised inside committed database transfers.
- Fresh seed verification: 20 customers, 30 accounts, 22 devices, **426 transfers,
  426 persisted predictions and 8 trigger-generated alerts**. Alert counts can
  vary with model artifact, threshold and UTC execution time.
- Actual PostgreSQL and SQLite rollback demos failed inference after balance updates
  and transaction insertion. Balances/counts/relevant audit counts were unchanged.
- Actual simultaneous ₹8,000/₹7,000 debits from ₹10,000 produced exactly one success,
  one insufficient-funds response, one prediction and conserved combined balances.
- Raw SQL prediction insertion triggered an alert without calling the transfer service.
- Alert/customer updates recorded old/new audit JSON; contact fields were excluded.
- Streamlit AppTest exercised transfer submission and audit inspection against the
  migrated API on both databases. The running PostgreSQL banking page was also
  opened and visually inspected in the Codex browser.
- `docs/dbms_demo.sql` executed on PostgreSQL with `ON_ERROR_STOP=1`.
- Measured customer/time query plan used **Index Only Scan** on
  `idx_transactions_customer_timestamp`; the observed execution time was 0.026 ms
  on the small local demo database. This is not a comparative speedup benchmark.
- Production OpenAPI excludes `/demo/*` routes.

The PostgreSQL service was started with Docker Compose. Host API and Streamlit
startup were verified. The optional backend Docker image build was not executed.
Generated dataset/model/report/database files remain gitignored. The pre-existing
user deletion of `pyproject.toml` was preserved; `pytest.ini` restores test import paths.

## Reproduce

```bash
export PYTHONPATH=src:.
export DATABASE_URL='postgresql+psycopg://frauddetect:local_demo_password@localhost:5432/frauddetect'
alembic upgrade head
TEST_DATABASE_URL="$DATABASE_URL" python -m pytest -q
python scripts/demo_concurrency.py
python scripts/demo_rollback.py
docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U frauddetect -d frauddetect < docs/dbms_demo.sql
```
