"""Versioned canonical evidence, bounded prefix validation and replay."""

import hashlib
import json
from datetime import timedelta, timezone
from decimal import Decimal

from sqlalchemy import select

from app.db.models import (
    BankingTransaction,
    CertificateEvidence,
    FlowCertificate,
    LedgerEntry,
    utcnow,
)
from app.services.flow_bounds import funding_bounds

CAP = 10000


def utc(value):
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def digest(payload):
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def entry_record(e):
    return {
        "account_id": e.account_id,
        "seq": e.seq,
        "transaction_id": e.transaction_id,
        "side": e.side,
        "amount": f"{e.amount:.2f}",
        "before": f"{e.balance_before:.2f}",
        "after": f"{e.balance_after:.2f}",
        "recorded_at": utc(e.recorded_at).isoformat(),
    }


def calculate(payload):
    rows = payload["entries"]
    target = rows[-1]
    history = [r for r in rows[:-1] if r["role"] == "HISTORY"]
    opening = Decimal(payload["opening_balance"])
    balance = opening
    seq = payload["opening_seq"]
    last_time = None
    for row in history + [target]:
        if row["seq"] != seq + 1 or Decimal(row["before"]) != balance:
            raise ValueError("Sequence or balance gap")
        if last_time and row["recorded_at"] < last_time:
            raise ValueError("Timestamp regression")
        amount = Decimal(row["amount"])
        balance += amount if row["side"] == "CREDIT" else -amount
        if balance < 0 or balance != Decimal(row["after"]):
            raise ValueError("Invalid movement arithmetic")
        seq, last_time = row["seq"], row["recorded_at"]
    lower, upper = funding_bounds(
        opening,
        [(r["side"], Decimal(r["amount"])) for r in history],
        Decimal(target["amount"]),
    )
    counterparties = len({r["counterparty"] for r in history if r["side"] == "CREDIT"})
    amount = Decimal(target["amount"])
    return {
        "lower_amount": str(lower),
        "upper_amount": str(upper),
        "lower_share": str(lower / amount),
        "upper_share": str(upper / amount),
        "ambiguity_width": str((upper - lower) / amount),
        "counterparties": counterparties,
        "review": lower / amount >= Decimal("0.80") and counterparties >= 3,
    }


def persist_flow(session, transaction, source, destination):
    now = utc(utcnow())
    for account in (source, destination):
        previous = (
            session.get(LedgerEntry, (account.account_id, account.ledger_seq))
            if account.ledger_seq
            else None
        )
        if previous:
            now = max(now, utc(previous.recorded_at))
    entries = []
    for account, side, before, after in (
        (source, "DEBIT", transaction.balance_before, transaction.balance_after),
        (
            destination,
            "CREDIT",
            transaction.destination_balance_before,
            transaction.destination_balance_after,
        ),
    ):
        account.ledger_seq += 1
        entry = LedgerEntry(
            account_id=account.account_id,
            seq=account.ledger_seq,
            transaction_id=transaction.transaction_id,
            side=side,
            amount=transaction.amount,
            balance_before=before,
            balance_after=after,
            recorded_at=now,
        )
        session.add(entry)
        entries.append(entry)
    session.flush()
    target = entries[0]
    start = now - timedelta(minutes=10)
    history_query = select(
        LedgerEntry,
        BankingTransaction.account_id,
        BankingTransaction.destination_account_id,
    ).join(
        BankingTransaction,
        BankingTransaction.transaction_id == LedgerEntry.transaction_id,
    )
    anchor_row = session.execute(
        history_query.where(
            LedgerEntry.account_id == source.account_id,
            LedgerEntry.seq < target.seq,
            LedgerEntry.recorded_at < start,
        )
        .order_by(LedgerEntry.recorded_at.desc(), LedgerEntry.seq.desc())
        .limit(1)
    ).first()
    anchor = anchor_row[0] if anchor_row else None
    opening_seq = anchor.seq if anchor else 0
    history_rows = session.execute(
        history_query.where(
            LedgerEntry.account_id == source.account_id,
            LedgerEntry.seq > opening_seq,
            LedgerEntry.seq < target.seq,
        )
        .order_by(LedgerEntry.seq)
        .limit(CAP + 1)
    ).all()
    history = [row[0] for row in history_rows]
    counterparties = {
        e.seq: incoming if e.side == "CREDIT" else outgoing
        for e, incoming, outgoing in ([anchor_row] if anchor_row else []) + history_rows
    }
    counterparties[target.seq] = destination.account_id
    opening = (
        anchor.balance_after
        if anchor
        else history[0].balance_before
        if history
        else target.balance_before
    )
    selected = ([anchor] if anchor else []) + history[:CAP] + [target]
    records = []
    for e in selected:
        r = entry_record(e)
        r["role"] = (
            "TARGET" if e is target else "OPENING_ANCHOR" if e is anchor else "HISTORY"
        )
        r["counterparty"] = counterparties[e.seq]
        records.append(r)
    payload = {
        "algorithm": "fabc-decimal-v1",
        "policy": "10m-80pct-3credits-v1",
        "window_start": start.isoformat(),
        "window_end": now.isoformat(),
        "opening_seq": opening_seq,
        "opening_balance": f"{opening:.2f}",
        "entries": records,
        "status": "VALID",
        "reason": None,
        "result": None,
    }
    try:
        if len(history) > CAP:
            raise ValueError("History cap exceeded")
        if (
            not anchor
            and source.ledger_started_at
            and start < utc(source.ledger_started_at)
        ):
            raise ValueError("Window precedes ledger observation start")
        payload["result"] = calculate(payload)
    except ValueError as exc:
        payload.update(status="INCOMPLETE", reason=str(exc), result=None)
    certificate = FlowCertificate(
        transaction_id=transaction.transaction_id,
        account_id=source.account_id,
        target_seq=target.seq,
        target_amount=target.amount,
        status=payload["status"],
        lower_amount=Decimal(payload["result"]["lower_amount"])
        if payload["result"]
        else None,
        upper_amount=Decimal(payload["result"]["upper_amount"])
        if payload["result"]
        else None,
        review=payload["result"]["review"] if payload["result"] else False,
        algorithm_version=payload["algorithm"],
        policy_version=payload["policy"],
        payload=payload,
        evidence_digest=digest(payload),
    )
    session.add(certificate)
    session.flush()
    for ordinal, r in enumerate(records):
        session.add(
            CertificateEvidence(
                certificate_id=certificate.certificate_id,
                account_id=r["account_id"],
                seq=r["seq"],
                ordinal=ordinal,
                role=r["role"],
            )
        )
    session.flush()
    return certificate


def replay(session, certificate):
    payload = certificate.payload
    matches = digest(payload) == certificate.evidence_digest
    target = payload["entries"][-1]
    expected_result = payload["result"]
    matches = matches and (
        target["transaction_id"] == certificate.transaction_id
        and target["account_id"] == certificate.account_id
        and target["seq"] == certificate.target_seq
        and target["side"] == "DEBIT"
        and Decimal(target["amount"]) == certificate.target_amount
        and payload["status"] == certificate.status
        and payload["algorithm"] == certificate.algorithm_version == "fabc-decimal-v1"
        and payload["policy"] == certificate.policy_version == "10m-80pct-3credits-v1"
        and (Decimal(expected_result["lower_amount"]) if expected_result else None)
        == certificate.lower_amount
        and (Decimal(expected_result["upper_amount"]) if expected_result else None)
        == certificate.upper_amount
        and (expected_result["review"] if expected_result else False)
        == certificate.review
    )
    evidence = session.execute(
        select(
            CertificateEvidence,
            LedgerEntry,
            BankingTransaction.account_id,
            BankingTransaction.destination_account_id,
        )
        .join(
            LedgerEntry,
            (LedgerEntry.account_id == CertificateEvidence.account_id)
            & (LedgerEntry.seq == CertificateEvidence.seq),
        )
        .join(
            BankingTransaction,
            BankingTransaction.transaction_id == LedgerEntry.transaction_id,
        )
        .where(CertificateEvidence.certificate_id == certificate.certificate_id)
        .order_by(CertificateEvidence.ordinal)
    ).all()
    matches = matches and len(evidence) == len(payload["entries"])
    for ordinal, ((membership, live, incoming, outgoing), stored) in enumerate(
        zip(evidence, payload["entries"])
    ):
        matches = (
            matches
            and membership.ordinal == ordinal
            and all(stored[k] == v for k, v in entry_record(live).items())
            and membership.role == stored["role"]
            and stored["counterparty"]
            == (incoming if live.side == "CREDIT" else outgoing)
        )
    result = calculate(payload) if payload["status"] == "VALID" and matches else None
    return {
        "verified": matches and result == payload["result"],
        "status": payload["status"],
        "result": result,
    }
