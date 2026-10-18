"""Persist ordered funding evidence without inventing history for existing accounts."""

import sqlalchemy as sa

from alembic import op
from app.db.models import CertificateEvidence, FlowCertificate, LedgerEntry

revision = "0003"
down_revision = "0002"
branch_labels = depends_on = None


def upgrade():
    op.add_column(
        "accounts", sa.Column("ledger_started_at", sa.DateTime(timezone=True))
    )
    op.execute("UPDATE accounts SET ledger_started_at = CURRENT_TIMESTAMP")
    op.add_column(
        "accounts",
        sa.Column("ledger_seq", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column("transactions", sa.Column("idempotency_key", sa.String(64)))
    op.add_column("transactions", sa.Column("request_digest", sa.String(64)))
    op.create_index(
        "uq_transfer_idempotency", "transactions", ["idempotency_key"], unique=True
    )
    for table in (
        LedgerEntry.__table__,
        FlowCertificate.__table__,
        CertificateEvidence.__table__,
    ):
        table.create(op.get_bind())
    # Updates are forbidden. Deletes remain protected by evidence FKs; isolated demo
    # fixtures are retained rather than silently removing certificates.
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        for name in ("ledger_entries", "flow_certificates", "certificate_evidence"):
            for action in ("UPDATE", "DELETE"):
                op.execute(
                    f"CREATE TRIGGER immutable_{name}_{action.lower()} BEFORE {action} ON {name} BEGIN SELECT RAISE(ABORT, 'immutable evidence'); END"
                )
    else:
        op.execute(
            "CREATE FUNCTION reject_evidence_update() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'immutable evidence'; END $$"
        )
        for name in ("ledger_entries", "flow_certificates", "certificate_evidence"):
            op.execute(
                f"CREATE TRIGGER immutable_{name} BEFORE UPDATE OR DELETE ON {name} FOR EACH ROW EXECUTE FUNCTION reject_evidence_update()"
            )


def downgrade():
    for table in (
        CertificateEvidence.__table__,
        FlowCertificate.__table__,
        LedgerEntry.__table__,
    ):
        table.drop(op.get_bind())
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP FUNCTION reject_evidence_update()")
    op.drop_index("uq_transfer_idempotency", table_name="transactions")
    op.drop_column("transactions", "request_digest")
    op.drop_column("transactions", "idempotency_key")
    op.drop_column("accounts", "ledger_seq")
    op.drop_column("accounts", "ledger_started_at")
