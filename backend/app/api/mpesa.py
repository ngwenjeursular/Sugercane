from fastapi import APIRouter, HTTPException

from app.services.mpesa import get_mpesa_access_token

router = APIRouter(prefix="/mpesa")


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