"""Disposable SQLite end-to-end benchmark using the configured fitted model."""

import json
import tempfile
from pathlib import Path
from time import perf_counter
from unittest.mock import patch

import numpy as np
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from alembic import command
from app.db.models import Account, Customer, FlowCertificate
from app.db.session import make_engine
from app.schemas import TransactionCreate
from app.services.flow_evidence import replay
from app.services.inference import ModelInference
from app.services.transactions import process_transfer
from app.settings import settings


def run(enabled):
    with tempfile.TemporaryDirectory() as directory:
        engine = make_engine(f"sqlite:///{directory}/benchmark.db")
        config = Config("alembic.ini")
        with engine.connect() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        factory = sessionmaker(engine, expire_on_commit=False)
        with factory() as s, s.begin():
            s.add(
                Customer(
                    customer_id="BENCH",
                    name="Synthetic benchmark",
                    email="bench@example.test",
                )
            )
            s.flush()
            s.add_all(
                [
                    Account(account_id="BA", customer_id="BENCH", balance=1000000),
                    Account(account_id="BB", customer_id="BENCH", balance=1000000),
                ]
            )
        model = ModelInference(settings.model_path)
        _ = model.model  # Exclude lazy artifact loading from transfer latency.
        times = []

        def noop(*args):
            return None

        from app.services.flow_evidence import persist_flow

        with patch(
            "app.services.transactions.persist_flow", persist_flow if enabled else noop
        ):
            for i in range(100):
                request = TransactionCreate(
                    customer_id="BENCH",
                    account_id="BA" if i % 2 else "BB",
                    destination_account_id="BB" if i % 2 else "BA",
                    amount="100.00",
                )
                before = perf_counter()
                with factory() as s:
                    process_transfer(s, request, model)
                times.append((perf_counter() - before) * 1000)
        with factory() as s:
            certs = s.scalars(select(FlowCertificate)).all()
            agreement = all(replay(s, c)["verified"] for c in certs)
            plan = [
                list(r)
                for r in s.execute(
                    text(
                        "EXPLAIN QUERY PLAN SELECT * FROM ledger_entries WHERE account_id='BA' AND recorded_at >= '2026-01-01' ORDER BY recorded_at, seq"
                    )
                )
            ]
        result = {
            "transfers": 100,
            "persisted_certificates": len(certs),
            "replay_agreement": agreement if certs else None,
            "latency_ms": dict(
                zip(("p50", "p95", "p99"), np.percentile(times, [50, 95, 99]).tolist())
            ),
            "throughput_per_second": 100 / (sum(times) / 1000),
            "max_evidence_rows": max(
                (len(c.payload["entries"]) for c in certs), default=0
            ),
            "certificate_json_bytes": sum(
                len(json.dumps(c.payload).encode()) for c in certs
            ),
            "query_plan": plan,
        }
        engine.dispose()
        return result


if __name__ == "__main__":
    result = {
        "dialect": "sqlite",
        "with_certificate": run(True),
        "without_certificate": run(False),
        "limitations": "Sequential local synthetic workload, warm fitted model; no PostgreSQL lock-wait or concurrent throughput claim.",
    }
    path = Path("reports/metrics/flow_database_benchmark.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
