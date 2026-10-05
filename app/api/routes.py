from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import Account, AuditLog, Customer, Device, FraudAlert, utcnow
from app.db.models import BankingTransaction as T
from app.db.models import FraudPrediction as P
from app.db.session import get_session
from app.schemas import (
    AccountCreate,
    AlertUpdate,
    CustomerCreate,
    CustomerUpdate,
    DeviceCreate,
    TransactionCreate,
)
from app.services.analytics import (
    customer_summary,
    database_overview,
    index_plan,
    record,
    statistics,
    transaction_query,
    transaction_record,
)
from app.services.inference import ModelInference
from app.services.transactions import BankingError, process_transfer
from app.settings import settings

router = APIRouter()
DB = Annotated[Session, Depends(get_session)]
inference = ModelInference(settings.model_path)


def get_inference():
    return inference


ML = Annotated[ModelInference, Depends(get_inference)]


def required(session, entity, key):
    obj = session.get(entity, key)
    if obj is None:
        raise BankingError(f"{entity.__name__} not found", 404)
    return obj


def insert(session, entity, request):
    obj = entity(**request.model_dump(exclude_none=True))
    session.add(obj)
    session.commit()
    return record(obj)


@router.get("/customers")
def customers(
    db: DB, limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0)
):
    return [
        record(x)
        for x in db.scalars(
            select(Customer).order_by(Customer.customer_id).offset(offset).limit(limit)
        )
    ]


@router.post("/customers", status_code=201)
def create_customer(request: CustomerCreate, db: DB):
    return insert(db, Customer, request)


@router.get("/customers/{customer_id}")
def customer(customer_id: str, db: DB):
    return record(required(db, Customer, customer_id))


@router.patch("/customers/{customer_id}")
def update_customer(customer_id: str, request: CustomerUpdate, db: DB):
    with db.begin():
        obj = db.scalar(
            select(Customer)
            .where(Customer.customer_id == customer_id)
            .with_for_update()
        )
        if obj is None:
            raise BankingError("Customer not found", 404)
        obj.status = request.status
    return record(obj)


@router.get("/customers/{customer_id}/risk-summary")
def risk_summary(customer_id: str, db: DB):
    summary = customer_summary(db, customer_id)
    if summary is None:
        raise BankingError("Customer not found", 404)
    return summary


@router.get("/accounts")
def accounts(
    db: DB, customer_id: str | None = None, limit: int = Query(100, ge=1, le=1000)
):
    query = select(Account).order_by(Account.account_id).limit(limit)
    if customer_id:
        query = query.where(Account.customer_id == customer_id)
    return [record(x) for x in db.scalars(query)]


@router.post("/accounts", status_code=201)
def create_account(request: AccountCreate, db: DB):
    return insert(db, Account, request)


@router.get("/devices")
def devices(
    db: DB, customer_id: str | None = None, limit: int = Query(100, ge=1, le=1000)
):
    query = select(Device).order_by(Device.device_id).limit(limit)
    if customer_id:
        query = query.where(Device.customer_id == customer_id)
    return [record(x) for x in db.scalars(query)]


@router.post("/devices", status_code=201)
def create_device(request: DeviceCreate, db: DB):
    return insert(db, Device, request)


@router.post("/transactions", status_code=201)
def create_transaction(request: TransactionCreate, db: DB, model: ML):
    transaction = process_transfer(db, request, model)
    return transaction_record(
        db.execute(
            transaction_query().where(T.transaction_id == transaction.transaction_id)
        ).one()
    )


@router.get("/transactions")
def transactions(
    db: DB,
    customer_id: str | None = None,
    suspicious_only: bool = False,
    min_amount: float = Query(0, ge=0),
    min_risk: float = Query(0, ge=0, le=1),
    since: datetime | None = None,
    until: datetime | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    query = transaction_query().where(T.amount >= min_amount)
    if customer_id:
        query = query.where(T.customer_id == customer_id)
    if suspicious_only:
        query = query.where(P.classification != "NORMAL")
    if min_risk:
        query = query.where(P.risk_score >= min_risk)
    if since:
        query = query.where(T.transaction_timestamp >= since)
    if until:
        query = query.where(T.transaction_timestamp <= until)
    return [
        transaction_record(row)
        for row in db.execute(
            query.order_by(T.transaction_timestamp.desc()).offset(offset).limit(limit)
        )
    ]


@router.get("/customers/{customer_id}/transactions")
def customer_transactions(
    customer_id: str, db: DB, limit: int = Query(100, ge=1, le=1000)
):
    required(db, Customer, customer_id)
    return transactions(
        db, customer_id=customer_id, min_amount=0, min_risk=0, limit=limit, offset=0
    )


@router.get("/transactions/{transaction_id}")
def transaction(transaction_id: str, db: DB):
    row = db.execute(
        transaction_query().where(T.transaction_id == transaction_id)
    ).first()
    if row is None:
        raise BankingError("Transaction not found", 404)
    return transaction_record(row)


@router.get("/transactions/{transaction_id}/prediction")
def prediction(transaction_id: str, db: DB):
    obj = db.scalar(select(P).where(P.transaction_id == transaction_id))
    if obj is None:
        raise BankingError("Prediction not found", 404)
    return record(obj)


@router.get("/fraud/alerts")
def alerts(db: DB, status: str | None = None, limit: int = Query(100, ge=1, le=1000)):
    query = (
        select(FraudAlert, T, P, Customer.name)
        .join(T, T.transaction_id == FraudAlert.transaction_id)
        .join(P, P.prediction_id == FraudAlert.prediction_id)
        .join(Customer, Customer.customer_id == T.customer_id)
    )
    if status:
        query = query.where(FraudAlert.alert_status == status)
    return [
        {
            **record(a),
            "customer_name": name,
            "customer_id": t.customer_id,
            "amount": t.amount,
            "fraud_probability": p.fraud_probability,
            "reasons": p.reasons,
        }
        for a, t, p, name in db.execute(
            query.order_by(FraudAlert.created_at.desc()).limit(limit)
        )
    ]


@router.get("/fraud/alerts/{alert_id}")
def alert(alert_id: str, db: DB):
    return record(required(db, FraudAlert, alert_id))


@router.patch("/fraud/alerts/{alert_id}")
def update_alert(alert_id: str, request: AlertUpdate, db: DB):
    with db.begin():
        if db.bind.dialect.name == "postgresql":
            db.execute(
                text("SELECT set_config('app.actor', :actor, true)"),
                {"actor": request.reviewed_by},
            )
        obj = db.scalar(
            select(FraudAlert).where(FraudAlert.alert_id == alert_id).with_for_update()
        )
        if obj is None:
            raise BankingError("Alert not found", 404)
        obj.alert_status = request.alert_status
        obj.reviewed_by = request.reviewed_by
        obj.reviewed_at = utcnow() if request.alert_status != "OPEN" else None
    return record(obj)


@router.get("/fraud/suspicious-transactions")
def suspicious(db: DB, limit: int = Query(100, ge=1, le=1000)):
    return [
        dict(x)
        for x in db.execute(
            text(
                "SELECT * FROM suspicious_transactions_view ORDER BY risk_score DESC LIMIT :limit"
            ),
            {"limit": limit},
        ).mappings()
    ]


@router.get("/fraud/statistics")
def stats(db: DB):
    return statistics(db)


@router.get("/audit-logs")
def audit(
    db: DB, table_name: str | None = None, limit: int = Query(100, ge=1, le=1000)
):
    query = select(AuditLog)
    if table_name:
        query = query.where(AuditLog.table_name == table_name)
    return [
        record(x)
        for x in db.scalars(
            query.order_by(AuditLog.changed_at.desc(), AuditLog.audit_id).limit(limit)
        )
    ]


@router.get("/database/overview")
def database(db: DB):
    return database_overview(db)


if settings.app_env == "development":

    @router.post("/demo/rollback")
    def demo_rollback(model: ML):
        from app.db.session import SessionLocal
        from app.services.demos import rollback_demo

        return rollback_demo(SessionLocal, model)

    @router.post("/demo/concurrency")
    def demo_concurrency(model: ML):
        from app.db.session import SessionLocal
        from app.services.demos import concurrency_demo

        return concurrency_demo(SessionLocal, model)

    @router.get("/demo/index-performance")
    def explain(db: DB, customer_id: str = "C001"):
        return index_plan(db, customer_id)
