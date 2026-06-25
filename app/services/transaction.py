from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select 


async def create_transaction(db: AsyncSession, data: TransactionCreate) -> TransactionResponse:
    async with db.begin():
        try:
            # Attempt to insert the new transaction
            new_transaction = Transaction(
                idempotency_key=data.idempotency_key,
                user_id=data.user_id,
                type=data.type,
                amount=data.amount,
                extra_data=data.extra_data
            )
            db.add(new_transaction)
            await db.flush()  # Flush to get the ID of the new transaction

        except IntegrityError as e:
            # Handle unique constraint violation (idempotency key)
            if "unique constraint" in str(e.orig):
                existing_transaction = await db.execute(
                    select(Transaction).where(Transaction.idempotency_key == data.idempotency_key)
                )
                existing_transaction = existing_transaction.scalar_one_or_none()
                if existing_transaction:
                    return TransactionResponse.from_orm(existing_transaction)
            raise e  # Re-raise if it's a different integrity error

        # Update user snapshot atomically
        user_snapshot = await db.execute(
            select(UserSnapshot).where(UserSnapshot.user_id == data.user_id).with_for_update()
        )
        user_snapshot = user_snapshot.scalar_one_or_none()

        if not user_snapshot:
            # Create a new snapshot if it doesn't exist
            user_snapshot = UserSnapshot(user_id=data.user_id, total_earned=0, total_spent=0)
            db.add(user_snapshot)

        # Update aggregates based on transaction type
        if data.type == "earn":
            user_snapshot.total_earned += data.amount
        elif data.type == "spend":
            user_snapshot.total_spent += data.amount

    return TransactionResponse.from_orm(new_transaction)
