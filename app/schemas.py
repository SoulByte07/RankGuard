from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    idempotency_key: str = Field(..., max_length=255, min_length=1)
    user_id: UUID
    type: Literal["earn", "spend", "bonus"]
    amount: Decimal = Field(..., gt=0, decimal_places=2)
    extra_data: dict | None = None


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    idempotency_key: str
    user_id: UUID
    type: str
    amount: Decimal
    created_at: datetime

class SummaryResponse(BaseModel):
     user_id: UUID
     total_earned: Decimal
     total_spent: Decimal
     net_balance: Decimal
     transaction_count: int
     bonus_count: int
     rank: int | None
     last_activity: datetime
 
