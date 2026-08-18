from decimal import Decimal, ROUND_DOWN

from sqlalchemy.orm import Session

from app.models import (
    FinancialTransaction,
    LedgerEntry,
    ReferralRule,
    User,
    Wallet,
)


def create_referral_commissions(
    db: Session,
    referred_user: User,
    deposit_transaction: FinancialTransaction,
):
    """
    Create referral commissions for a completed deposit.

    Level 1 = direct referrer
    Level 2 = referrer's referrer
    Level 3 = third level

    Commissions are credited to the respective referral wallets.
    """

    if deposit_transaction.status != "completed":
        return []

    rules = (
        db.query(ReferralRule)
        .filter(
            ReferralRule.active.is_(True),
            ReferralRule.level.in_([1, 2, 3]),
        )
        .all()
    )

    rules_by_level = {
        rule.level: rule
        for rule in rules
    }

    commissions = []

    current_user = referred_user

    for level in range(1, 4):
        parent_id = current_user.referred_by_id

        if not parent_id:
            break

        parent = (
            db.query(User)
            .filter(User.id == parent_id)
            .first()
        )

        if not parent:
            break

        rule = rules_by_level.get(level)

        if not rule:
            current_user = parent
            continue

        commission = (
            deposit_transaction.amount
            * rule.rate_percent
            / Decimal("100")
        ).quantize(
            Decimal("0.01"),
            rounding=ROUND_DOWN,
        )

        if commission <= 0:
            current_user = parent
            continue

        wallet = (
            db.query(Wallet)
            .filter(Wallet.user_id == parent.id)
            .first()
        )

        if not wallet:
            current_user = parent
            continue

        commission_transaction = FinancialTransaction(
            reference=f"REF-{deposit_transaction.reference}-{level}",
            user_id=parent.id,
            transaction_type="referral_commission",
            status="completed",
            amount=commission,
            currency=wallet.currency,
            external_reference=(
                f"{deposit_transaction.reference}:REF:{level}"
            ),
            completed_at=deposit_transaction.completed_at,
        )

        db.add(commission_transaction)
        db.flush()

        ledger_entry = LedgerEntry(
            wallet_id=wallet.id,
            transaction_id=commission_transaction.id,
            direction="credit",
            amount=commission,
        )

        db.add(ledger_entry)

        commissions.append(
            {
                "level": level,
                "user_id": str(parent.id),
                "amount": commission,
                "transaction_id": commission_transaction.id,
            }
        )

        current_user = parent

    return commissions