import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, Numeric, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TransactionType(str, enum.Enum):
    earn = "earn"
    spend = "spend"
    bonus = "bonus"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    snapshot: Mapped["UserSnapshot"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    ranking: Mapped["Ranking"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(nullable=False, unique=True)
    type: Mapped[TransactionType] = mapped_column(SAEnum(TransactionType, name="transaction_type"), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserSnapshot(Base):
    __tablename__ = "user_snapshots"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    total_earned: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    total_spent: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    net_balance: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    transaction_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bonus_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    user: Mapped["User"] = relationship(back_populates="snapshot")


class Ranking(Base):
    __tablename__ = "rankings"

    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    score: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="ranking")
