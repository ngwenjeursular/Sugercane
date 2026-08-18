import hashlib, secrets, hmac
from datetime import datetime, timedelta, timezone
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from app.core.config import get_settings

_hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)
def hash_password(password: str) -> str: return _hasher.hash(password)
def verify_password(password: str, password_hash: str) -> bool:
    try: return _hasher.verify(password_hash, password)
    except VerificationError: return False
def new_token() -> str: return secrets.token_urlsafe(32)
def token_hash(token: str) -> str: return hashlib.sha256(token.encode()).hexdigest()
def expires_at(): return datetime.now(timezone.utc) + timedelta(hours=get_settings().session_ttl_hours)
def safe_equal(a,b): return hmac.compare_digest(a,b)
