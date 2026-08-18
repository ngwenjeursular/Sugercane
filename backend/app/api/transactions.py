from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.api.deps import current_user
from app.db.session import get_db
from app.models import FinancialTransaction, LedgerEntry, User, Wallet
from app.schemas.transactions import (
    TestDepositRequest,
    WithdrawalRequest,
)
from app.services.transactions import create_completed_deposit
from uuid import uuid4


router = APIRouter(prefix="/transactions")
settings = get_settings()


@router.post("/test-deposit")
def test_deposit(
    payload: TestDepositRequest,
    db: Session = Depends(get_db),
):
    """
    DEVELOPMENT ONLY.

    Simulates an externally confirmed deposit.
    """

    user = (
        db.query(User)
        .filter(User.id == payload.user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found.",
        )

    try:
        transaction, commissions = create_completed_deposit(
            db=db,
            user=user,
            amount=payload.amount,
            external_reference=payload.external_reference,
        )

        db.commit()

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        db.rollback()
        raise

    return {
        "message": "Deposit completed.",
        "transaction": {
            "id": str(transaction.id),
            "reference": transaction.reference,
            "type": transaction.transaction_type,
            "status": transaction.status,
            "amount": f"{Decimal(transaction.amount):.2f}",
            "currency": transaction.currency,
            "external_reference": transaction.external_reference,
            "completed_at": transaction.completed_at.isoformat(),
        },
        "referral_commissions": [
            {
                "level": commission["level"],
                "user_id": commission["user_id"],
                "amount": f"{commission['amount']:.2f}",
            }
            for commission in commissions
        ],
    }

@router.post("/withdraw")
def request_withdrawal(
    payload: WithdrawalRequest,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    amount = payload.amount

    # SERVER-SIDE minimum.
    # The frontend cannot override this value.
    minimum = settings.withdrawal_minimum

    if amount < minimum:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Minimum withdrawal amount is "
                f"KSh {minimum:.2f}."
            ),
        )

    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == user.id)
        .first()
    )

    if not wallet:
        raise HTTPException(
            status_code=400,
            detail="User does not have a wallet.",
        )

    # Calculate actual wallet balance.
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

    # Pending withdrawals are not yet debited from the ledger,
    # so subtract them when determining available funds.
    pending_withdrawals = (
        db.query(
            func.coalesce(
                func.sum(FinancialTransaction.amount),
                0,
            )
        )
        .filter(
            FinancialTransaction.user_id == user.id,
            FinancialTransaction.transaction_type == "withdrawal",
            FinancialTransaction.status == "pending",
        )
        .scalar()
    )

    pending_withdrawals = Decimal(
        str(pending_withdrawals)
    )

    available_balance = balance - pending_withdrawals

    if amount > available_balance:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Insufficient available balance. "
                f"Available balance is "
                f"KSh {available_balance:.2f}."
            ),
        )

    transaction = FinancialTransaction(
        reference=f"WDR-{uuid4().hex[:20].upper()}",
        user_id=user.id,
        transaction_type="withdrawal",
        status="pending",
        amount=amount,
        currency=wallet.currency,
    )

    db.add(transaction)
    db.commit()
    db.refresh(transaction)

    return {
        "message": "Withdrawal request submitted.",
        "withdrawal": {
            "id": str(transaction.id),
            "reference": transaction.reference,
            "type": transaction.transaction_type,
            "status": transaction.status,
            "amount": f"{transaction.amount:.2f}",
            "currency": transaction.currency,
        },
    }