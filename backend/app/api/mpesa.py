from base64 import b64encode
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import csrf, current_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import User, FinancialTransaction

from app.services.mpesa import (
    get_mpesa_access_token,
    initiate_stk_push,
    query_stk_push,
    normalize_mpesa_phone,
)

from app.services.transactions import (
    create_pending_mpesa_deposit,
    complete_mpesa_deposit,
)


settings = get_settings()

router = APIRouter(prefix="/mpesa")


# ============================================================
# REQUEST MODELS
# ============================================================

class STKPushRequest(BaseModel):
    amount: Decimal = Field(gt=0)


# ============================================================
# M-PESA PASSWORD
# ============================================================

def generate_mpesa_password(timestamp: str) -> str:
    raw = (
        f"{settings.mpesa_shortcode}"
        f"{settings.mpesa_passkey}"
        f"{timestamp}"
    )

    return b64encode(
        raw.encode("utf-8")
    ).decode("utf-8")


# ============================================================
# TEST DARAJA OAUTH
# ============================================================

@router.get("/test-token")
def test_token():
    try:
        token = get_mpesa_access_token()

        return {
            "message": "Daraja OAuth successful.",
            "token_received": bool(token),
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Daraja OAuth failed: {str(exc)}",
        )


# ============================================================
# TEST M-PESA PASSWORD
# ============================================================

@router.get("/test-password")
def test_password():
    timestamp = "20260818133443"

    return {
        "BusinessShortCode": settings.mpesa_shortcode,
        "Timestamp": timestamp,
        "password_generated": generate_mpesa_password(timestamp),
    }


# ============================================================
# STK PUSH
# ============================================================

@router.post("/stkpush")
def stk_push(
    request: STKPushRequest,
    user: User = Depends(current_user),
    _: None = Depends(csrf),
    db: Session = Depends(get_db),
):
    # --------------------------------------------------------
    # Validate deposit amount
    # --------------------------------------------------------

    if request.amount < settings.deposit_minimum:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Minimum deposit amount is "
                f"KSh {settings.deposit_minimum:.2f}."
            ),
        )

    if request.amount != request.amount.to_integral_value():
        raise HTTPException(
            status_code=400,
            detail=(
                "Deposit amount must be a whole number "
                "of Kenyan shillings."
            ),
        )

    try:
        # ----------------------------------------------------
        # Initiate STK Push
        # ----------------------------------------------------

        result = initiate_stk_push(
            amount=request.amount,
            phone_number=user.phone_number,
            account_reference=f"DEP-{user.id}",
            transaction_description="Sugercane wallet deposit",
        )

        checkout_request_id = result.get(
            "CheckoutRequestID"
        )

        if not checkout_request_id:
            raise ValueError(
                "M-Pesa did not return a CheckoutRequestID."
            )

        # ----------------------------------------------------
        # Create pending transaction
        # ----------------------------------------------------

        transaction = create_pending_mpesa_deposit(
            db=db,
            user=user,
            amount=request.amount,
            checkout_request_id=checkout_request_id,
        )

        db.commit()

        return {
            **result,
            "transaction_reference": transaction.reference,
            "transaction_status": transaction.status,
        }

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=502,
            detail=f"STK Push failed: {str(exc)}",
        )


# ============================================================
# M-PESA CALLBACK
# ============================================================

@router.post("/callback")
async def mpesa_callback(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Receives the asynchronous STK callback from Safaricom.

    The callback contains the authoritative payment result and,
    for successful payments, the M-Pesa receipt, amount, and
    phone number.

    The wallet is only credited after complete_mpesa_deposit()
    successfully validates the callback.
    """

    print("\n=== M-PESA CALLBACK DEBUG ===")

    try:
        # ----------------------------------------------------
        # 1. Capture raw callback
        # ----------------------------------------------------

        raw_body = await request.body()

        print("Callback headers:")
        print(dict(request.headers))

        print("Raw callback body:")
        print(
            raw_body.decode(
                "utf-8",
                errors="replace",
            )
        )

        # ----------------------------------------------------
        # 2. Parse JSON
        # ----------------------------------------------------

        try:
            payload = await request.json()

        except Exception as exc:
            print(
                "Callback JSON parsing failed:",
                str(exc),
            )

            return {
                "ResultCode": 0,
                "ResultDesc": "Callback received",
            }

        print("Parsed callback payload:")
        print(payload)

        # ----------------------------------------------------
        # 3. Extract STK callback
        # ----------------------------------------------------

        stk_callback = (
            payload
            .get("Body", {})
            .get("stkCallback")
        )

        if not stk_callback:
            raise ValueError(
                "M-Pesa callback did not contain Body.stkCallback."
            )

        checkout_request_id = stk_callback.get(
            "CheckoutRequestID"
        )

        if not checkout_request_id:
            raise ValueError(
                "M-Pesa callback did not contain "
                "CheckoutRequestID."
            )

        result_code_raw = stk_callback.get(
            "ResultCode"
        )

        if result_code_raw is None:
            raise ValueError(
                "M-Pesa callback did not contain ResultCode."
            )

        result_code = int(result_code_raw)

        # ----------------------------------------------------
        # 4. Extract callback metadata
        # ----------------------------------------------------

        mpesa_receipt = None
        callback_amount = None
        callback_phone = None

        if result_code == 0:
            callback_metadata = (
                stk_callback
                .get("CallbackMetadata", {})
                .get("Item", [])
            )

            for item in callback_metadata:
                name = item.get("Name")
                value = item.get("Value")

                if name == "MpesaReceiptNumber":
                    if value is not None:
                        mpesa_receipt = str(value)

                elif name == "Amount":
                    if value is not None:
                        callback_amount = Decimal(
                            str(value)
                        )

                elif name == "PhoneNumber":
                    if value is not None:
                        callback_phone = str(value)

        # ----------------------------------------------------
        # 5. Debug extracted values
        # ----------------------------------------------------

        print(
            "CheckoutRequestID:",
            checkout_request_id,
        )

        print(
            "ResultCode:",
            result_code,
        )

        print(
            "M-Pesa receipt:",
            mpesa_receipt,
        )

        print(
            "Callback amount:",
            callback_amount,
        )

        print(
            "Callback phone:",
            callback_phone,
        )

        # ----------------------------------------------------
        # 6. Complete transaction
        # ----------------------------------------------------

        transaction, commissions = complete_mpesa_deposit(
            db=db,
            checkout_request_id=checkout_request_id,
            result_code=result_code,
            mpesa_receipt=mpesa_receipt,
            callback_amount=callback_amount,
            callback_phone=callback_phone,
        )

        db.commit()

        print(
            "M-Pesa transaction processed:",
            transaction.reference,
            transaction.status,
        )

        print("============================\n")

        return {
            "ResultCode": 0,
            "ResultDesc": "Callback processed successfully",
        }

    except ValueError as exc:
        db.rollback()

        print(
            "M-Pesa callback processing error:"
        )

        print(str(exc))

        print("============================\n")

        # ----------------------------------------------------
        # Acknowledge callback
        #
        # We acknowledge the callback even if our internal
        # processing failed so Safaricom does not repeatedly
        # resend it.
        # ----------------------------------------------------

        return {
            "ResultCode": 0,
            "ResultDesc": "Callback received",
        }

    except Exception as exc:
        db.rollback()

        print(
            "M-Pesa callback unexpected error:"
        )

        print(repr(exc))

        print("============================\n")

        # ----------------------------------------------------
        # Acknowledge callback
        # ----------------------------------------------------

        return {
            "ResultCode": 0,
            "ResultDesc": "Callback received",
        }


# ============================================================
# M-PESA RECONCILIATION
# ============================================================

@router.post("/reconcile/{checkout_request_id}")
def reconcile_mpesa_transaction(
    checkout_request_id: str,
    user: User = Depends(current_user),
    _: None = Depends(csrf),
    db: Session = Depends(get_db),
):
    """
    Recover a pending M-Pesa deposit when the asynchronous
    callback was not received.

    The browser cannot tell us whether a payment succeeded.

    Instead:

    1. Find the transaction in our database.
    2. Verify it belongs to the authenticated user.
    3. Verify it is still pending.
    4. Query Safaricom using the stored CheckoutRequestID.
    5. Use Safaricom's ResultCode to determine the result.
    6. Complete the transaction through the transaction service.
    """

    try:
        # ----------------------------------------------------
        # 1. Find transaction
        # ----------------------------------------------------

        transaction = (
            db.query(FinancialTransaction)
            .filter(
                FinancialTransaction.mpesa_checkout_request_id
                == checkout_request_id,
                FinancialTransaction.user_id
                == user.id,
            )
            .with_for_update()
            .first()
        )

        if not transaction:
            raise HTTPException(
                status_code=404,
                detail="M-Pesa transaction not found.",
            )

        # ----------------------------------------------------
        # 2. Idempotency
        # ----------------------------------------------------

        if transaction.status == "completed":
            return {
                "status": "completed",
                "message": (
                    "Payment has already been completed."
                ),
                "transaction_reference": (
                    transaction.reference
                ),
            }

        if transaction.status == "failed":
            return {
                "status": "failed",
                "message": (
                    "This M-Pesa transaction has "
                    "already failed."
                ),
                "transaction_reference": (
                    transaction.reference
                ),
            }

        # ----------------------------------------------------
        # 3. Query Safaricom
        # ----------------------------------------------------

        result = query_stk_push(
            checkout_request_id
        )

        print(
            "\n=== M-PESA RECONCILIATION ==="
        )

        print(
            "Transaction:",
            transaction.reference,
        )

        print(
            "Daraja response:",
            result,
        )

        print(
            "============================="
        )

        # ----------------------------------------------------
        # 4. Read ResultCode
        # ----------------------------------------------------

        result_code_raw = result.get(
            "ResultCode"
        )

        if result_code_raw is None:
            raise ValueError(
                "M-Pesa status response did not "
                "contain ResultCode."
            )

        result_code = int(
            result_code_raw
        )

        # ----------------------------------------------------
        # 5. Successful payment
        # ----------------------------------------------------

        if result_code == 0:

            # ------------------------------------------------
            # STK Query normally confirms the transaction
            # but does not necessarily return CallbackMetadata.
            #
            # In that case, use the controlled recovery path.
            # The amount and user come from our own pending
            # transaction, not from the browser.
            # ------------------------------------------------

            callback_metadata = (
                result.get("CallbackMetadata")
                or {}
            )

            items = callback_metadata.get(
                "Item"
            ) or []

            mpesa_receipt = None
            callback_amount = None
            callback_phone = None

            for item in items:
                name = item.get("Name")
                value = item.get("Value")

                if name == "MpesaReceiptNumber":
                    if value is not None:
                        mpesa_receipt = str(value)

                elif name == "Amount":
                    if value is not None:
                        callback_amount = Decimal(
                            str(value)
                        )

                elif name == "PhoneNumber":
                    if value is not None:
                        callback_phone = str(value)

            # ------------------------------------------------
            # Metadata available
            # ------------------------------------------------

            if (
                mpesa_receipt
                and callback_amount is not None
                and callback_phone is not None
            ):

                transaction, commissions = (
                    complete_mpesa_deposit(
                        db=db,
                        checkout_request_id=checkout_request_id,
                        result_code=0,
                        mpesa_receipt=mpesa_receipt,
                        callback_amount=callback_amount,
                        callback_phone=callback_phone,
                    )
                )

                db.commit()

                print(
                    "M-Pesa payment reconciled:",
                    transaction.reference,
                )

                return {
                    "status": "completed",
                    "message": (
                        "M-Pesa payment successfully "
                        "reconciled."
                    ),
                    "transaction_reference": (
                        transaction.reference
                    ),
                    "transaction_status": (
                        transaction.status
                    ),
                    "mpesa_receipt": mpesa_receipt,
                    "recovered": False,
                }

            # ------------------------------------------------
            # Recovery path
            # ------------------------------------------------
            #
            # Safaricom confirmed ResultCode == 0 for this
            # exact CheckoutRequestID, but STK Query did not
            # provide CallbackMetadata.
            #
            # complete_mpesa_deposit() uses the transaction
            # already stored in our database and does not
            # trust browser-supplied payment information.
            # ------------------------------------------------

            transaction, commissions = (
                complete_mpesa_deposit(
                    db=db,
                    checkout_request_id=checkout_request_id,
                    result_code=0,
                    recovery=True,
                )
            )

            db.commit()

            print(
                "M-Pesa payment recovered:",
                transaction.reference,
            )

            return {
                "status": "completed",
                "message": (
                    "M-Pesa payment successfully "
                    "reconciled."
                ),
                "transaction_reference": (
                    transaction.reference
                ),
                "transaction_status": (
                    transaction.status
                ),
                "mpesa_receipt": None,
                "recovered": True,
            }

        # ----------------------------------------------------
        # 6. Failed / cancelled payment
        # ----------------------------------------------------

        transaction, commissions = (
            complete_mpesa_deposit(
                db=db,
                checkout_request_id=checkout_request_id,
                result_code=result_code,
            )
        )

        db.commit()

        return {
            "status": "failed",
            "message": result.get(
                "ResultDesc",
                "M-Pesa transaction failed.",
            ),
            "transaction_reference": (
                transaction.reference
            ),
            "transaction_status": (
                transaction.status
            ),
            "result_code": result_code,
        }

    except HTTPException:
        db.rollback()
        raise

    except ValueError as exc:
        db.rollback()

        print(
            "M-Pesa reconciliation validation error:"
        )

        print(str(exc))

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        db.rollback()

        print(
            "M-Pesa reconciliation error:"
        )

        print(repr(exc))

        raise HTTPException(
            status_code=502,
            detail=(
                "M-Pesa reconciliation failed: "
                f"{str(exc)}"
            ),
        )