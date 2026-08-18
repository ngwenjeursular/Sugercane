from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.db.session import get_db
from app.models import User, Wallet, LedgerEntry, FinancialTransaction

router = APIRouter(prefix="/users")


@router.get("/me")
def get_me(
    user: User = Depends(current_user),
):
    return {
        "id": str(user.id),
        "full_name": user.full_name,
        "phone_number": user.phone_number,
        "referral_code": user.referral_code,
    }


@router.get("/wallet")
def get_wallet(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    wallet = (
        db.query(Wallet)
        .filter(Wallet.user_id == user.id)
        .first()
    )

    if not wallet:
        return {
            "currency": "KES",
            "balance": "0.00",
            "status": "inactive",
        }

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

    return {
        "currency": wallet.currency,
        "balance": f"{balance:.2f}",
        "status": wallet.status,
    }


@router.get("/transactions")
def get_transactions(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    transactions = (
        db.query(FinancialTransaction)
        .filter(FinancialTransaction.user_id == user.id)
        .order_by(FinancialTransaction.created_at.desc())
        .limit(20)
        .all()
    )

    return [
        {
            "id": str(transaction.id),
            "reference": transaction.reference,
            "type": transaction.transaction_type,
            "status": transaction.status,
            "amount": f"{transaction.amount:.2f}",
            "currency": transaction.currency,
            "created_at": transaction.created_at.isoformat(),
        }
        for transaction in transactions
    ]


@router.get("/referrals")
def get_referrals(
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    direct_referrals = (
        db.query(User)
        .filter(User.referred_by_id == user.id)
        .count()
    )

    return {
        "referral_code": user.referral_code,
        "direct_referrals": direct_referrals,
        "total_referrals": direct_referrals,
        "earnings": "0.00",
        "currency": "KES",
    }