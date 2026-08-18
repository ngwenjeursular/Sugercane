from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from decimal import Decimal

class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str
    session_cookie_name: str = "sugercane_session"
    csrf_cookie_name: str = "sugercane_csrf"
    session_ttl_hours: int = 24
    cookie_secure: bool = True
    allowed_origins: str = ""
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    withdrawal_minimum: Decimal = Decimal("1000.00")
    mpesa_environment: str
    mpesa_consumer_key: str
    mpesa_consumer_secret: str
    mpesa_base_url: str
    
    @property
    def origins(self): return [x.strip() for x in self.allowed_origins.split(",") if x.strip()]

@lru_cache
def get_settings(): return Settings()
