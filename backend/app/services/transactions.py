from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import FinancialTransaction, LedgerEntry, User, Wallet
from app.services.referrals import create_referral_commissions


def create_completed_deposit(
    db: Session,
    user: User,
    amount: Decimal,
    external_reference: str,
):
    """
    Development deposit service.

    Creates:
    1. A completed deposit transaction.
    2. A credit to the depositor's wallet.
    3. Referral commissions for eligible upline users.

    The API layer commits the database transaction after this
    function completes successfully.
    """

    existing = (
        db.query(FinancialTransaction)
        .filter(
            FinancialTransaction.external_reference
            == external_reference
        )
        .first()
    )

    if existing:
        raise ValueError(
            "A transaction with this external reference already exists."
        )

    if amount <= Decimal("0"):
        raise ValueError(
            "Deposit amount must be greater than zero."
        )

    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == user.id)
        .first()
    )

    if not wallet:
        raise ValueError(
            "User does not have a wallet."
        )

    completed_at = datetime.now(timezone.utc)

    # ---------------------------------------------------------
    # 1. Create the deposit transaction
    # ---------------------------------------------------------

    transaction = FinancialTransaction(
        reference=f"DEP-{uuid4().hex[:20].upper()}",
        user_id=user.id,
        transaction_type="deposit",
        status="completed",
        amount=amount,
        currency=wallet.currency,
        external_reference=external_reference,
        completed_at=completed_at,
    )

    db.add(transaction)
    db.flush()

    # ---------------------------------------------------------
    # 2. Credit the depositor's wallet
    # ---------------------------------------------------------

    ledger_entry = LedgerEntry(
        wallet_id=wallet.id,
        transaction_id=transaction.id,
        direction="credit",
        amount=amount,
    )

    db.add(ledger_entry)

    # ---------------------------------------------------------
    # 3. Create referral commissions
    # ---------------------------------------------------------

    commissions = create_referral_commissions(
        db=db,
        referred_user=user,
        deposit_transaction=transaction,
    )

    return transaction, commissions

def create_withdrawal_request(
    db: Session,
    user: User,
    amount: Decimal,
    idempotency_key: str,
):
    """
    Creates a pending withdrawal request.

    The external payment system is responsible for actually
    sending the money. The wallet is only debited once the
    withdrawal is successfully completed.
    """

    # Basic business-rule validation
    if amount < Decimal("1000.00"):
        raise ValueError(
            "Minimum withdrawal amount is KSh 1,000."
        )

    # Check for duplicate withdrawal requests
    existing = (
        db.query(FinancialTransaction)
        .filter(
            FinancialTransaction.idempotency_key
            == idempotency_key
        )
        .first()
    )

    if existing:
        raise ValueError(
            "A withdrawal with this idempotency key already exists."
        )

    # Find user's wallet
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == user.id)
        .first()
    )

    if not wallet:
        raise ValueError(
            "User does not have a wallet."
        )

    # Calculate current wallet balance
        # Calculate wallet balance
    credits = (
        db.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
        .filter(
            LedgerEntry.wallet_id == wallet.id,
            LedgerEntry.direction == "credit",
        )
        .scalar()
    )

    debits = (
        db.query(func.coalesce(func.sum(LedgerEntry.amount), 0))
        .filter(
            LedgerEntry.wallet_id == wallet.id,
            LedgerEntry.direction == "debit",
        )
        .scalar()
    )

    balance = Decimal(str(credits)) - Decimal(str(debits))

    # Pending withdrawals have not been debited from the ledger yet,
    # so subtract them when calculating what the user can actually withdraw.
    pending_withdrawals = (
        db.query(func.coalesce(func.sum(FinancialTransaction.amount), 0))
        .filter(
            FinancialTransaction.user_id == user.id,
            FinancialTransaction.transaction_type == "withdrawal",
            FinancialTransaction.status == "pending",
        )
        .scalar()
    )

    pending_withdrawals = Decimal(str(pending_withdrawals))

    available_balance = balance - pending_withdrawals

    if amount > available_balance:
        raise ValueError(
            f"Insufficient available balance. "
            f"Available balance is KSh {available_balance:.2f}."
        )
    # Create pending withdrawal transaction
    transaction = FinancialTransaction(
        reference=f"WDR-{uuid4().hex[:20].upper()}",
        user_id=user.id,
        transaction_type="withdrawal",
        status="pending",
        amount=amount,
        currency=wallet.currency,
        idempotency_key=idempotency_key,
    )

    db.add(transaction)
    db.flush()

    return transaction