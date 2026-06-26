import asyncio
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Transaction, TransactionType, User, UserSnapshot
from app.schemas import TransactionCreate, TransactionResponse

_user_locks: dict[UUID, asyncio.Lock] = {}
_lock_lock = asyncio.Lock()


async def _get_user_lock(user_id: UUID) -> asyncio.Lock:
    async with _lock_lock:
        if user_id not in _user_locks:
            _user_locks[user_id] = asyncio.Lock()
        return _user_locks[user_id]


async def create_transaction(
    db: AsyncSession, data: TransactionCreate
) -> tuple[TransactionResponse, bool]:
    """Returns (response, is_created)."""
    async with _get_user_lock(data.user_id):
        result = await db.execute(
            select(Transaction).where(Transaction.idempotency_key == data.idempotency_key)
        )
        existing = result.scalar_one_or_none()
        if existing:
            return TransactionResponse.model_validate(existing), False

        user = await db.get(User, data.user_id)
        if not user:
            user = User(id=data.user_id)
            db.add(user)

        result = await db.execute(
            select(UserSnapshot).where(UserSnapshot.user_id == data.user_id).with_for_update()
        )
        snapshot = result.scalar_one_or_none()
        if not snapshot:
            snapshot = UserSnapshot(user_id=data.user_id)
            db.add(snapshot)

        new_tx = Transaction(
            idempotency_key=data.idempotency_key,
            user_id=data.user_id,
            type=TransactionType(data.type),
            amount=data.amount,
            extra_data=data.extra_data,
        )
        db.add(new_tx)

        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            result = await db.execute(
                select(Transaction).where(Transaction.idempotency_key == data.idempotency_key)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return TransactionResponse.model_validate(existing), False
            raise

        tx_type = TransactionType(data.type)
        if tx_type == TransactionType.earn:
            snapshot.total_earned += data.amount
            snapshot.net_balance += data.amount
        elif tx_type == TransactionType.spend:
            snapshot.total_spent += data.amount
            snapshot.net_balance -= data.amount
        elif tx_type == TransactionType.bonus:
            snapshot.bonus_count += 1
            snapshot.net_balance += data.amount

        snapshot.transaction_count += 1

        await db.commit()

        return TransactionResponse.model_validate(new_tx), True
