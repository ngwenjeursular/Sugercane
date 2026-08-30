from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    FinancialTransaction,
    LedgerEntry,
    User,
    Wallet,
)
from app.services.mpesa import normalize_mpesa_phone
from app.services.referrals import create_referral_commissions


def create_pending_mpesa_deposit(
    db: Session,
    user: User,
    amount: Decimal,
    checkout_request_id: str,
):
    """
    Create a pending M-Pesa deposit.

    The wallet is NOT credited here.
    The wallet is credited only after a successful
    M-Pesa callback or successful server-side reconciliation.
    """

    existing = (
        db.query(FinancialTransaction)
        .filter(
            FinancialTransaction.mpesa_checkout_request_id
            == checkout_request_id
        )
        .first()
    )

    if existing:
        raise ValueError(
            "A transaction with this M-Pesa checkout request ID "
            "already exists."
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

    transaction = FinancialTransaction(
        reference=f"DEP-{uuid4().hex[:20].upper()}",
        user_id=user.id,
        transaction_type="deposit",
        status="pending",
        amount=amount,
        currency=wallet.currency,
        mpesa_checkout_request_id=checkout_request_id,
    )

    db.add(transaction)
    db.flush()

    return transaction


def complete_mpesa_deposit(
    db: Session,
    checkout_request_id: str,
    result_code: int,
    mpesa_receipt: str | None = None,
    callback_amount: Decimal | None = None,
    callback_phone: str | None = None,
    recovery: bool = False,
):
    """
    Complete an M-Pesa deposit safely.

    Normal callback:
    - requires an M-Pesa receipt
    - requires the callback amount
    - requires the callback phone
    - validates amount and phone
    - prevents receipt reuse

    Recovery:
    - is only used after the server has independently queried
      Daraja and received ResultCode == 0
    - does not require CallbackMetadata
    - uses the original transaction amount and user stored
      in our database
    - creates an internal recovery reference instead of
      pretending we received an M-Pesa receipt

    Both paths:
    - only process pending transactions
    - credit the wallet once
    - create referral commissions once
    """

    transaction = (
        db.query(FinancialTransaction)
        .filter(
            FinancialTransaction.mpesa_checkout_request_id
            == checkout_request_id
        )
        .with_for_update()
        .first()
    )

    if not transaction:
        raise ValueError(
            "M-Pesa transaction not found."
        )

    # ---------------------------------------------------------
    # Idempotency
    # ---------------------------------------------------------

    if transaction.status != "pending":
        return transaction, []

    # ---------------------------------------------------------
    # Failed / cancelled transaction
    # ---------------------------------------------------------

    if result_code != 0:
        transaction.status = "failed"
        return transaction, []

    # ---------------------------------------------------------
    # Find the user
    # ---------------------------------------------------------

    user = (
        db.query(User)
        .filter(
            User.id == transaction.user_id
        )
        .first()
    )

    if not user:
        raise ValueError(
            "User associated with M-Pesa transaction was not found."
        )

    # ---------------------------------------------------------
    # Normal callback validation
    # ---------------------------------------------------------

    if not recovery:

        if not mpesa_receipt:
            raise ValueError(
                "Successful M-Pesa callback did not contain "
                "a receipt number."
            )

        if callback_amount is None:
            raise ValueError(
                "Successful M-Pesa callback did not contain "
                "an amount."
            )

        if callback_phone is None:
            raise ValueError(
                "Successful M-Pesa callback did not contain "
                "a phone number."
            )

        # Amount must match the amount we originally requested.
        if callback_amount != transaction.amount:
            raise ValueError(
                "M-Pesa callback amount does not match "
                "the transaction amount."
            )

        # Normalize both phone numbers before comparison.
        expected_phone = normalize_mpesa_phone(
            user.phone_number
        )

        received_phone = normalize_mpesa_phone(
            str(callback_phone)
        )

        if received_phone != expected_phone:
            raise ValueError(
                "M-Pesa callback phone number does not match "
                "the user's account."
            )

    # ---------------------------------------------------------
    # Prevent reuse of an M-Pesa receipt
    # ---------------------------------------------------------

    if mpesa_receipt:

        existing_receipt = (
            db.query(FinancialTransaction)
            .filter(
                FinancialTransaction.external_reference
                == mpesa_receipt,
                FinancialTransaction.id
                != transaction.id,
            )
            .first()
        )

        if existing_receipt:
            raise ValueError(
                "This M-Pesa receipt has already been processed."
            )

    # ---------------------------------------------------------
    # Find wallet
    # ---------------------------------------------------------

    wallet = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == transaction.user_id
        )
        .first()
    )

    if not wallet:
        raise ValueError(
            "User does not have a wallet."
        )

    # ---------------------------------------------------------
    # Prevent duplicate ledger credit
    # ---------------------------------------------------------

    existing_ledger = (
        db.query(LedgerEntry)
        .filter(
            LedgerEntry.transaction_id
            == transaction.id
        )
        .first()
    )

    if existing_ledger:
        raise ValueError(
            "This M-Pesa transaction already has a ledger entry."
        )

    # ---------------------------------------------------------
    # Complete transaction
    # ---------------------------------------------------------

    transaction.status = "completed"
    transaction.completed_at = datetime.now(timezone.utc)

    if mpesa_receipt:
        transaction.external_reference = mpesa_receipt

    elif recovery:
        transaction.external_reference = (
            f"STK-RECOVERY-{checkout_request_id}"
        )

    # ---------------------------------------------------------
    # Credit wallet
    # ---------------------------------------------------------

    ledger_entry = LedgerEntry(
        wallet_id=wallet.id,
        transaction_id=transaction.id,
        direction="credit",
        amount=transaction.amount,
    )

    db.add(ledger_entry)

    # ---------------------------------------------------------
    # Referral commissions
    # ---------------------------------------------------------

    commissions = create_referral_commissions(
        db=db,
        referred_user=user,
        deposit_transaction=transaction,
    )

    return transaction, commissions


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
    3. Referral commissions.

    The API layer commits the database transaction.
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
            "A transaction with this external reference "
            "already exists."
        )

    if amount <= Decimal("0"):
        raise ValueError(
            "Deposit amount must be greater than zero."
        )

    wallet = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == user.id
        )
        .first()
    )

    if not wallet:
        raise ValueError(
            "User does not have a wallet."
        )

    completed_at = datetime.now(timezone.utc)

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

    ledger_entry = LedgerEntry(
        wallet_id=wallet.id,
        transaction_id=transaction.id,
        direction="credit",
        amount=amount,
    )

    db.add(ledger_entry)

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

    The wallet is only debited after the external
    payment succeeds.
    """

    # ---------------------------------------------------------
    # Minimum withdrawal amount
    # ---------------------------------------------------------

    if amount < Decimal("1000.00"):
        raise ValueError(
            "Minimum withdrawal amount is KSh 1,000."
        )

    # ---------------------------------------------------------
    # Idempotency
    # ---------------------------------------------------------

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
            "A withdrawal with this idempotency key "
            "already exists."
        )

    # ---------------------------------------------------------
    # Find wallet
    # ---------------------------------------------------------

    wallet = (
        db.query(Wallet)
        .filter(
            Wallet.user_id == user.id
        )
        .first()
    )

    if not wallet:
        raise ValueError(
            "User does not have a wallet."
        )

    # ---------------------------------------------------------
    # Calculate wallet balance
    # ---------------------------------------------------------

    credits = (
        db.query(
            func.coalesce(
                func.sum(LedgerEntry.amount),
                0,
            )
        )
        .filter(
            LedgerEntry.wallet_id == wallet.id,
            LedgerEntry.direction == "credit",
        )
        .scalar()
    )

    debits = (
        db.query(
            func.coalesce(
                func.sum(LedgerEntry.amount),
                0,
            )
        )
        .filter(
            LedgerEntry.wallet_id == wallet.id,
            LedgerEntry.direction == "debit",
        )
        .scalar()
    )

    balance = (
        Decimal(str(credits))
        - Decimal(str(debits))
    )

    # ---------------------------------------------------------
    # Account for pending withdrawals
    # ---------------------------------------------------------

    pending_withdrawals = (
        db.query(
            func.coalesce(
                func.sum(FinancialTransaction.amount),
                0,
            )
        )
        .filter(
            FinancialTransaction.user_id == user.id,
            FinancialTransaction.transaction_type
            == "withdrawal",
            FinancialTransaction.status == "pending",
        )
        .scalar()
    )

    pending_withdrawals = Decimal(
        str(pending_withdrawals)
    )

    available_balance = (
        balance - pending_withdrawals
    )

    if amount > available_balance:
        raise ValueError(
            "Insufficient available balance. "
            f"Available balance is "
            f"KSh {available_balance:.2f}."
        )

    # ---------------------------------------------------------
    # Create pending withdrawal
    # ---------------------------------------------------------

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