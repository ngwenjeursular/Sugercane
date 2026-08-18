from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class User(Base):
    __tablename__="users"
    id: Mapped[UUID]=mapped_column(primary_key=True,default=uuid4)
    phone_number: Mapped[str]=mapped_column(String(13),unique=True,index=True)
    full_name: Mapped[str]=mapped_column(String(100))
    password_hash: Mapped[str]=mapped_column(String(512))
    referral_code: Mapped[str]=mapped_column(String(24),unique=True,index=True)
    referred_by_id: Mapped[UUID|None]=mapped_column(ForeignKey("users.id",ondelete="SET NULL"),nullable=True,index=True)
    is_active: Mapped[bool]=mapped_column(Boolean,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    referred_by=relationship("User",remote_side=[id],back_populates="referrals")
    referrals=relationship("User",back_populates="referred_by")
    wallet=relationship("Wallet",back_populates="user",uselist=False,cascade="all, delete-orphan")

class Session(Base):
    __tablename__="sessions"
    id: Mapped[UUID]=mapped_column(primary_key=True,default=uuid4)
    user_id: Mapped[UUID]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),index=True)
    token_hash: Mapped[str]=mapped_column(String(64),unique=True,index=True)
    csrf_hash: Mapped[str]=mapped_column(String(64))
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))

class Wallet(Base):
    __tablename__="wallets"
    id: Mapped[UUID]=mapped_column(primary_key=True,default=uuid4)
    user_id: Mapped[UUID]=mapped_column(ForeignKey("users.id",ondelete="CASCADE"),unique=True,index=True)
    currency: Mapped[str]=mapped_column(String(3),default="KES")
    status: Mapped[str]=mapped_column(String(16),default="active")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    user=relationship("User",back_populates="wallet")
    ledger_entries=relationship("LedgerEntry",back_populates="wallet")

class FinancialTransaction(Base):
    __tablename__="transactions"
    id: Mapped[UUID]=mapped_column(primary_key=True,default=uuid4)
    reference: Mapped[str]=mapped_column(String(32),unique=True,index=True)
    user_id: Mapped[UUID]=mapped_column(ForeignKey("users.id",ondelete="RESTRICT"),index=True)
    transaction_type: Mapped[str]=mapped_column(String(32))
    status: Mapped[str]=mapped_column(String(16))
    amount: Mapped[Decimal]=mapped_column(Numeric(18,2))
    currency: Mapped[str]=mapped_column(String(3),default="KES")
    external_reference: Mapped[str|None]=mapped_column(String(128),unique=True,nullable=True,index=True)
    idempotency_key: Mapped[str|None]=mapped_column(String(128),unique=True,nullable=True,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    completed_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)

class LedgerEntry(Base):
    __tablename__="ledger_entries"
    id: Mapped[UUID]=mapped_column(primary_key=True,default=uuid4)
    wallet_id: Mapped[UUID]=mapped_column(ForeignKey("wallets.id",ondelete="RESTRICT"),index=True)
    transaction_id: Mapped[UUID]=mapped_column(ForeignKey("transactions.id",ondelete="RESTRICT"),index=True)
    direction: Mapped[str]=mapped_column(String(8))
    amount: Mapped[Decimal]=mapped_column(Numeric(18,2))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    wallet=relationship("Wallet",back_populates="ledger_entries")

class ReferralRule(Base):
    __tablename__="referral_rules"
    id: Mapped[UUID]=mapped_column(primary_key=True,default=uuid4)
    level: Mapped[int]=mapped_column(Integer)
    rate_percent: Mapped[Decimal]=mapped_column(Numeric(7,4))
    active: Mapped[bool]=mapped_column(Boolean,default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
    __table_args__=(UniqueConstraint("level",name="uq_referral_rules_level"),)
