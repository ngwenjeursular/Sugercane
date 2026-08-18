from alembic import op
import sqlalchemy as sa

revision = "0003_update_referral_rates"
down_revision = "0002_referrals"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
        UPDATE referral_rules
        SET rate_percent = 5
        WHERE level = 1
        """
    )

    op.execute(
        """
        UPDATE referral_rules
        SET rate_percent = 2
        WHERE level = 2
        """
    )

    op.execute(
        """
        UPDATE referral_rules
        SET rate_percent = 1
        WHERE level = 3
        """
    )


def downgrade():
    op.execute(
        """
        UPDATE referral_rules
        SET rate_percent = 5
        WHERE level = 1
        """
    )

    op.execute(
        """
        UPDATE referral_rules
        SET rate_percent = 1
        WHERE level = 2
        """
    )

    op.execute(
        """
        UPDATE referral_rules
        SET rate_percent = 0.5
        WHERE level = 3
        """
    )