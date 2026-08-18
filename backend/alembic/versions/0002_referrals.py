from alembic import op
import sqlalchemy as sa
from uuid import uuid4
from datetime import datetime,timezone
revision="0002_referrals"; down_revision="0001_initial"; branch_labels=None; depends_on=None
def upgrade():
    table=sa.table("referral_rules",sa.column("id",sa.UUID()),sa.column("level",sa.Integer()),sa.column("rate_percent",sa.Numeric(7,4)),sa.column("active",sa.Boolean()),sa.column("created_at",sa.DateTime(timezone=True)))
    op.bulk_insert(table,[{"id":uuid4(),"level":1,"rate_percent":5,"active":True,"created_at":datetime.now(timezone.utc)},{"id":uuid4(),"level":2,"rate_percent":1,"active":True,"created_at":datetime.now(timezone.utc)},{"id":uuid4(),"level":3,"rate_percent":0.5,"active":True,"created_at":datetime.now(timezone.utc)}])
def downgrade(): op.execute("DELETE FROM referral_rules")
