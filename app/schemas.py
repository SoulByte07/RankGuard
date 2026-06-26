from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_serializer


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

    @field_serializer("amount")
    def serialize_amount(self, v: Decimal) -> float:
        return float(v)


class SummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    total_earned: Decimal
    total_spent: Decimal
    net_balance: Decimal
    transaction_count: int
    bonus_count: int
    rank: int | None
    last_activity: datetime

    @field_serializer("total_earned", "total_spent", "net_balance")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v)


class RankingEntry(BaseModel):
    rank: int
    user_id: UUID
    score: Decimal
    total_earned: Decimal
    total_spent: Decimal
    transaction_count: int

    @field_serializer("score", "total_earned", "total_spent")
    def serialize_decimal(self, v: Decimal) -> float:
        return float(v)


class RankingListResponse(BaseModel):
    count: int
    results: list[RankingEntry]
