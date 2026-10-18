# ruff: noqa: F811
from decimal import Decimal as D
from itertools import product

import pytest
from sqlalchemy import func, select

from app.db.models import Account, FlowCertificate, LedgerEntry
from app.services.flow_bounds import funding_bounds
from app.services.flow_evidence import replay
from app.services.transactions import BankingError, process_transfer
from tests.test_banking import TestInference, factory, transfer  # noqa: F401


def test_report_examples():
    assert funding_bounds(
        D(1000),
        [("CREDIT", D(x)) for x in (4000, 3000, 2000)] + [("DEBIT", D(2000))],
        D(7500),
    ) == (D(6500), D(7500))
    assert funding_bounds(D(100000), [("CREDIT", D(9000))], D(7500)) == (D(0), D(7500))


def test_exhaustive_allocation_oracle():
    for opening in range(4):
        for events in product(
            (("CREDIT", 1), ("CREDIT", 2), ("DEBIT", 1), ("DEBIT", 2)), repeat=4
        ):
            balance, feasible = opening, {0}
            for side, amount in events:
                if side == "CREDIT":
                    feasible = {r + amount for r in feasible}
                    balance += amount
                elif amount <= balance:
                    feasible = {
                        r - spend
                        for r in feasible
                        for spend in range(amount + 1)
                        if spend <= r and amount - spend <= balance - r
                    }
                    balance -= amount
                else:
                    break
            else:
                for target in range(1, balance + 1):
                    allocations = {
                        spend
                        for r in feasible
                        for spend in range(target + 1)
                        if spend <= r and target - spend <= balance - r
                    }
                    assert funding_bounds(D(opening), events, D(target)) == (
                        min(allocations),
                        max(allocations),
                    )


def test_persistence_replay_idempotency(factory):
    request = transfer(idempotency_key="retry-1")
    with factory() as s:
        tx = process_transfer(s, request, TestInference())
    with factory() as s:
        repeated = process_transfer(s, request, TestInference())
        assert repeated.transaction_id == tx.transaction_id
    with factory() as s:
        c = s.scalar(select(FlowCertificate))
        assert c.payload["status"] == "VALID"
        assert replay(s, c)["verified"]
        assert s.scalar(select(func.count()).select_from(LedgerEntry)) == 2
    with factory() as s, pytest.raises(BankingError):
        process_transfer(
            s, transfer(idempotency_key="retry-1", amount="2000"), TestInference()
        )


def test_certificate_failure_rolls_back(factory, monkeypatch):
    from app.services.flow_evidence import persist_flow

    def fail(*args):
        persist_flow(*args)
        raise RuntimeError("certificate failure after evidence writes")

    monkeypatch.setattr("app.services.transactions.persist_flow", fail)
    with factory() as s, pytest.raises(RuntimeError):
        process_transfer(s, transfer(), TestInference())
    with factory() as s:
        assert s.get(Account, "A1").balance == D(1000000)
        assert s.get(Account, "A1").ledger_seq == 0
        assert s.scalar(select(func.count()).select_from(LedgerEntry)) == 0


def test_cap_and_migration_epoch_are_incomplete(factory, monkeypatch):
    from app.db.models import utcnow

    with factory() as s, s.begin():
        s.get(Account, "A1").ledger_started_at = utcnow()
    with factory() as s:
        first = process_transfer(s, transfer(), TestInference())
    with factory() as s:
        c = s.scalar(
            select(FlowCertificate).where(
                FlowCertificate.transaction_id == first.transaction_id
            )
        )
        assert c.payload["status"] == "INCOMPLETE"
        assert c.payload["result"] is None
        assert replay(s, c)["verified"]
    monkeypatch.setattr("app.services.flow_evidence.CAP", 0)
    with factory() as s:
        second = process_transfer(s, transfer(), TestInference())
    with factory() as s:
        c = s.scalar(
            select(FlowCertificate).where(
                FlowCertificate.transaction_id == second.transaction_id
            )
        )
        assert c.payload["reason"] == "History cap exceeded"
        assert c.payload["result"] is None


def test_evidence_immutable_and_api_replay(factory):
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from app.db.session import get_session
    from app.main import app

    with factory() as s:
        tx = process_transfer(s, transfer(), TestInference())
    for statement in (
        "UPDATE ledger_entries SET amount=1",
        "DELETE FROM certificate_evidence",
        "DELETE FROM flow_certificates",
        "UPDATE transactions SET amount=1, balance_after=balance_before-1, destination_balance_after=destination_balance_before+1",
    ):
        with factory() as s, pytest.raises(DBAPIError):
            s.execute(text(statement))
            s.commit()

    def sessions():
        with factory() as s:
            yield s

    app.dependency_overrides[get_session] = sessions
    try:
        with TestClient(app) as client:
            base = f"/transactions/{tx.transaction_id}/flow-certificate"
            assert client.get(base).status_code == 200
            assert client.get(base + "/replay").json()["verified"]
    finally:
        app.dependency_overrides.clear()


def test_multiple_transfers_and_tampered_replay(factory):
    for _ in range(4):
        with factory() as s:
            process_transfer(s, transfer(), TestInference())
    with factory() as s:
        certificates = s.scalars(select(FlowCertificate)).all()
        assert all(replay(s, c)["verified"] for c in certificates)
        assert s.get(Account, "A1").ledger_seq == 4
        c = certificates[-1]
        c.payload = {**c.payload, "opening_balance": "123.45"}
        with s.no_autoflush:
            assert not replay(s, c)["verified"]


def test_report_example_a_saved_review(factory):
    with factory() as s, s.begin():
        s.get(Account, "A2").balance = D(1000)
        for account in ("A3", "A4", "A5"):
            s.add(Account(account_id=account, customer_id="C1", balance=D(10000)))
    for source, amount in zip(("A3", "A4", "A5"), ("4000", "3000", "2000")):
        with factory() as s:
            process_transfer(
                s, transfer(account_id=source, amount=amount), TestInference()
            )
    for amount in ("2000", "7500"):
        with factory() as s:
            tx = process_transfer(
                s,
                transfer(
                    customer_id="C2",
                    account_id="A2",
                    destination_account_id="A1",
                    device_id="D2",
                    amount=amount,
                ),
                TestInference(),
            )
    with factory() as s:
        c = s.scalar(
            select(FlowCertificate).where(
                FlowCertificate.transaction_id == tx.transaction_id
            )
        )
        assert c.lower_amount == D(6500)
        assert c.upper_amount == D(7500)
        assert c.review
        assert c.payload["result"]["counterparties"] == 3
        assert replay(s, c)["verified"]


@pytest.mark.parametrize(
    "age_seconds, expected_lower", [(599, "1000"), (600, "1000"), (601, "0")]
)
def test_window_boundary_and_opening_anchor(
    factory, monkeypatch, age_seconds, expected_lower
):
    from datetime import datetime, timedelta, timezone

    origin = datetime(2026, 10, 16, 12, tzinfo=timezone.utc)
    monkeypatch.setattr("app.services.flow_evidence.utcnow", lambda: origin)
    with factory() as s, s.begin():
        s.get(Account, "A2").balance = D(0)
    with factory() as s:
        process_transfer(s, transfer(amount="2000"), TestInference())
    monkeypatch.setattr(
        "app.services.flow_evidence.utcnow",
        lambda: origin + timedelta(seconds=age_seconds),
    )
    with factory() as s:
        tx = process_transfer(
            s,
            transfer(
                customer_id="C2",
                account_id="A2",
                destination_account_id="A1",
                device_id="D2",
            ),
            TestInference(),
        )
    with factory() as s:
        c = s.scalar(
            select(FlowCertificate).where(
                FlowCertificate.transaction_id == tx.transaction_id
            )
        )
        assert c.status == "VALID"
        assert c.lower_amount == D(expected_lower)
        assert replay(s, c)["verified"]


def test_missing_prefix_detected(factory):
    with factory() as s:
        process_transfer(s, transfer(), TestInference())
    # Simulate an unrecorded writer changing a balance. The next history validation
    # must refuse an exact interval, even though the transfer itself can still post.
    with factory() as s, s.begin():
        s.get(Account, "A1").balance += D(100)
    with factory() as s:
        tx = process_transfer(s, transfer(), TestInference())
    with factory() as s:
        c = s.scalar(
            select(FlowCertificate).where(
                FlowCertificate.transaction_id == tx.transaction_id
            )
        )
        assert c.status == "INCOMPLETE"
        assert c.lower_amount is None
        assert "gap" in c.payload["reason"]


def test_concurrent_retries_single_certificate(factory):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(2)

    def submit(_):
        barrier.wait(timeout=10)
        with factory() as s:
            return process_transfer(
                s, transfer(idempotency_key="simultaneous-retry"), TestInference()
            ).transaction_id

    with ThreadPoolExecutor(max_workers=2) as pool:
        ids = list(pool.map(submit, range(2)))
    assert ids[0] == ids[1]
    with factory() as s:
        assert s.scalar(select(func.count()).select_from(FlowCertificate)) == 1
        assert s.scalar(select(func.count()).select_from(LedgerEntry)) == 2
        assert s.get(Account, "A1").balance == D(999000)


def test_reconnect_persistence(factory):
    from sqlalchemy.orm import sessionmaker

    from app.db.session import make_engine

    with factory() as s:
        tx = process_transfer(s, transfer(), TestInference())
    engine = factory.kw["bind"]
    url = engine.url
    engine.dispose()
    # PostgreSQL fixture uses an isolated search_path configured on the original
    # engine; test a new pool there, and a wholly new engine for file-based SQLite.
    reopened = make_engine(str(url)) if engine.dialect.name == "sqlite" else engine
    try:
        with sessionmaker(reopened)() as s:
            certificate = s.scalar(
                select(FlowCertificate).where(
                    FlowCertificate.transaction_id == tx.transaction_id
                )
            )
            assert replay(s, certificate)["verified"]
    finally:
        if reopened is not engine:
            reopened.dispose()
