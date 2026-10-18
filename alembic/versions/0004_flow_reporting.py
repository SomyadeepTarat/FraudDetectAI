"""Protect certified transaction facts and expose certificate evidence joins."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = depends_on = None

FIELDS = (
    "account_id",
    "destination_account_id",
    "customer_id",
    "amount",
    "balance_before",
    "balance_after",
    "destination_balance_before",
    "destination_balance_after",
    "transaction_timestamp",
)


def upgrade():
    op.execute("""CREATE VIEW flow_certificate_detail_view AS
        SELECT c.certificate_id, c.transaction_id, c.account_id, c.target_seq,
               c.status, c.lower_amount, c.upper_amount, c.target_amount, c.review,
               c.algorithm_version, c.policy_version, c.evidence_digest,
               e.ordinal, e.role, l.seq, l.side, l.amount, l.balance_before,
               l.balance_after, l.recorded_at
        FROM flow_certificates c JOIN certificate_evidence e
          ON e.certificate_id = c.certificate_id
        JOIN ledger_entries l ON l.account_id = e.account_id AND l.seq = e.seq""")
    if op.get_bind().dialect.name == "sqlite":
        changed = " OR ".join(f"NEW.{f} IS NOT OLD.{f}" for f in FIELDS)
        op.execute(f"""CREATE TRIGGER protect_certified_transfer BEFORE UPDATE ON transactions
            WHEN ({changed}) AND EXISTS (SELECT 1 FROM ledger_entries WHERE transaction_id=OLD.transaction_id)
            BEGIN SELECT RAISE(ABORT, 'certified monetary facts are immutable'); END""")
    else:
        new = ",".join(f"NEW.{f}" for f in FIELDS)
        old = ",".join(f"OLD.{f}" for f in FIELDS)
        op.execute(f"""CREATE FUNCTION protect_certified_transfer() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN IF ROW({new}) IS DISTINCT FROM ROW({old}) AND EXISTS
                (SELECT 1 FROM ledger_entries WHERE transaction_id=OLD.transaction_id)
            THEN RAISE EXCEPTION 'certified monetary facts are immutable'; END IF;
            RETURN NEW; END $$""")
        op.execute("""CREATE TRIGGER protect_certified_transfer BEFORE UPDATE ON transactions
            FOR EACH ROW EXECUTE FUNCTION protect_certified_transfer()""")


def downgrade():
    if op.get_bind().dialect.name == "sqlite":
        op.execute("DROP TRIGGER protect_certified_transfer")
    else:
        op.execute("DROP TRIGGER protect_certified_transfer ON transactions")
        op.execute("DROP FUNCTION protect_certified_transfer()")
    op.execute("DROP VIEW flow_certificate_detail_view")
