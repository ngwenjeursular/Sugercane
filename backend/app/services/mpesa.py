import base64

import httpx

from app.core.config import get_settings


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