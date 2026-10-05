"""Disposable rows demonstrate real rollback and concurrent debits safely."""

from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

from sqlalchemy import func, select

from app.db.models import (
    Account,
    AuditLog,
    BankingTransaction,
    Customer,
    FraudAlert,
    FraudPrediction,
)
from app.schemas import TransactionCreate
from app.services.transactions import BankingError, process_transfer


def fixture(factory):
    suffix = uuid4().hex[:12]
    customer, source, destination = (
        f"{prefix}-{suffix}" for prefix in ("demo-c", "demo-a", "demo-b")
    )
    with factory() as session, session.begin():
        session.add(
            Customer(
                customer_id=customer,
                name="Disposable ACID demo",
                email=f"{suffix}@demo.example",
            )
        )
        session.flush()
        session.add_all(
            [
                Account(
                    account_id=source, customer_id=customer, balance=Decimal(10000)
                ),
                Account(
                    account_id=destination, customer_id=customer, balance=Decimal(0)
                ),
            ]
        )
    return customer, source, destination


def snapshot(factory, ids):
    customer, source, destination = ids
    with factory() as session:
        return {
            "source_balance": str(session.get(Account, source).balance),
            "destination_balance": str(session.get(Account, destination).balance),
            "transaction_count": session.scalar(
                select(func.count())
                .select_from(BankingTransaction)
                .where(BankingTransaction.customer_id == customer)
            ),
            "prediction_count": session.scalar(
                select(func.count())
                .select_from(FraudPrediction)
                .join(BankingTransaction)
                .where(BankingTransaction.customer_id == customer)
            ),
            "audit_count": session.scalar(
                select(func.count())
                .select_from(AuditLog)
                .where(AuditLog.record_id.in_(ids))
            ),
        }


def cleanup(factory, ids):
    with factory() as session, session.begin():
        txs = session.scalars(
            select(BankingTransaction).where(BankingTransaction.customer_id == ids[0])
        ).all()
        for tx in txs:
            for alert in session.scalars(
                select(FraudAlert).where(FraudAlert.transaction_id == tx.transaction_id)
            ):
                session.delete(alert)
            session.flush()
            for prediction in session.scalars(
                select(FraudPrediction).where(
                    FraudPrediction.transaction_id == tx.transaction_id
                )
            ):
                session.delete(prediction)
            session.flush()
            session.delete(tx)
        session.flush()
        for account_id in ids[1:]:
            session.delete(session.get(Account, account_id))
        session.flush()
        session.delete(session.get(Customer, ids[0]))
        # Trigger-generated audit entries deliberately remain as demonstration evidence.


def rollback_demo(factory, inference):
    ids = fixture(factory)
    before = snapshot(factory, ids)
    try:
        request = TransactionCreate(
            customer_id=ids[0],
            account_id=ids[1],
            destination_account_id=ids[2],
            amount="15000",
        )
        try:
            with factory() as session:
                process_transfer(session, request, inference)
        except BankingError as exc:
            error = exc.message
        else:
            raise AssertionError("Invalid transfer unexpectedly succeeded")
        after_insufficient = snapshot(factory, ids)

        # Fail inference after debit/credit and transaction insertion have really occurred.
        class BrokenInference:
            def predict(self, transaction):
                raise RuntimeError("intentional demo inference failure")

        request = request.model_copy(update={"amount": Decimal(1000)})
        try:
            with factory() as session:
                process_transfer(session, request, BrokenInference())
        except BankingError as exc:
            model_error = exc.message
        after = snapshot(factory, ids)
        assert before == after_insufficient == after
        return {
            "before": before,
            "after": after,
            "insufficient_balance_error": error,
            "failure_after_writes": model_error,
            "rollback_verified": True,
        }
    finally:
        cleanup(factory, ids)


def concurrency_demo(factory, inference):
    ids = fixture(factory)
    barrier = Barrier(2)

    def debit(amount):
        request = TransactionCreate(
            customer_id=ids[0],
            account_id=ids[1],
            destination_account_id=ids[2],
            amount=amount,
        )
        barrier.wait(timeout=10)
        try:
            with factory() as session:
                process_transfer(session, request, inference)
            return {"amount": amount, "success": True}
        except BankingError as exc:
            return {"amount": amount, "success": False, "error": exc.message}

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(debit, ["8000", "7000"]))
        after = snapshot(factory, ids)
        assert sum(result["success"] for result in results) == 1
        assert after["transaction_count"] == after["prediction_count"] == 1
        assert Decimal(after["source_balance"]) + Decimal(
            after["destination_balance"]
        ) == Decimal(10000)
        return {"requests": results, "after": after, "concurrency_verified": True}
    finally:
        cleanup(factory, ids)
