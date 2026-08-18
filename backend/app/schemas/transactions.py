from decimal import Decimal

from pydantic import BaseModel, Field


class TestDepositRequest(BaseModel):
    user_id: str
    amount: Decimal = Field(gt=0)
    external_reference: str = Field(min_length=1, max_length=128)


class WithdrawalRequest(BaseModel):
    amount: Decimal = Field(gt=0)