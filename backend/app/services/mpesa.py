import base64
from datetime import datetime
from decimal import Decimal

import httpx

from app.core.config import get_settings


def normalize_mpesa_phone(phone_number: str) -> str:
    phone = phone_number.strip()

    if phone.startswith("+254"):
        phone = phone[1:]

    elif phone.startswith("0"):
        phone = "254" + phone[1:]

    if not phone.startswith("254") or len(phone) != 12:
        raise ValueError(
            "Invalid Kenyan phone number format."
        )

    if not phone.isdigit():
        raise ValueError(
            "Phone number must contain digits only."
        )

    return phone


def get_mpesa_access_token() -> str:
    settings = get_settings()

    credentials = (
        f"{settings.mpesa_consumer_key}:"
        f"{settings.mpesa_consumer_secret}"
    )

    encoded_credentials = base64.b64encode(
        credentials.encode()
    ).decode()

    response = httpx.get(
        f"{settings.mpesa_base_url}/oauth/v1/generate"
        "?grant_type=client_credentials",
        headers={
            "Authorization": f"Basic {encoded_credentials}"
        },
        timeout=15.0,
    )

    response.raise_for_status()

    data = response.json()

    return data["access_token"]


def initiate_stk_push(
    amount: Decimal,
    phone_number: str,
    account_reference: str,
    transaction_description: str,
) -> dict:
    settings = get_settings()
    phone_number = normalize_mpesa_phone(phone_number)

    if amount <= 0:
        raise ValueError(
            "STK Push amount must be greater than zero."
        )

    if amount != amount.to_integral_value():
        raise ValueError(
            "STK Push amount must be a whole number of Kenyan shillings."
        )

    access_token = get_mpesa_access_token()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password_raw = (
        f"{settings.mpesa_shortcode}"
        f"{settings.mpesa_passkey}"
        f"{timestamp}"
    )

    password = base64.b64encode(
        password_raw.encode()
    ).decode()

    payload = {
        "BusinessShortCode": settings.mpesa_shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": str(int(amount)),
        "PartyA": phone_number,
        "PartyB": settings.mpesa_shortcode,
        "PhoneNumber": phone_number,
        "CallBackURL": settings.mpesa_callback_url,
        "AccountReference": account_reference,
        "TransactionDesc": transaction_description,
    }

    print("=== M-PESA STK DEBUG ===")
    print("Phone:", phone_number)
    print("Amount:", amount)
    print("Callback URL:", settings.mpesa_callback_url)
    print("Payload:", payload)
    print("========================")

    response = httpx.post(
        f"{settings.mpesa_base_url}/mpesa/stkpush/v1/processrequest",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30.0,
    )

    print("M-Pesa STK response:")
    print("Status:", response.status_code)
    print("Response:", response.text)

    if response.status_code >= 400:
        raise ValueError(
            f"M-Pesa API returned {response.status_code}: "
            f"{response.text}"
        )

    return response.json()


def query_stk_push(
    checkout_request_id: str,
) -> dict:
    """
    Queries Safaricom for the current status of an STK Push.
    """

    settings = get_settings()

    access_token = get_mpesa_access_token()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    password_raw = (
        f"{settings.mpesa_shortcode}"
        f"{settings.mpesa_passkey}"
        f"{timestamp}"
    )

    password = base64.b64encode(
        password_raw.encode()
    ).decode()

    payload = {
        "BusinessShortCode": settings.mpesa_shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }

    response = httpx.post(
        f"{settings.mpesa_base_url}/mpesa/stkpushquery/v1/query",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30.0,
    )

    print("=== M-PESA STK QUERY ===")
    print("CheckoutRequestID:", checkout_request_id)
    print("Status:", response.status_code)
    print("Response:", response.text)
    print("========================")

    response.raise_for_status()

    return response.json()