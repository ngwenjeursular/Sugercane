from alembic import op
import sqlalchemy as sa


revision = "0004_mpesa_checkout_request_id"
down_revision = "0003_update_referral_rates"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "transactions",
        sa.Column(
            "mpesa_checkout_request_id",
            sa.String(length=128),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_transactions_mpesa_checkout_request_id",
        "transactions",
        ["mpesa_checkout_request_id"],
        unique=True,
    )


def downgrade():
    op.drop_index(
        "ix_transactions_mpesa_checkout_request_id",
        table_name="transactions",
    )

    op.drop_column(
        "transactions",
        "mpesa_checkout_request_id",
    )