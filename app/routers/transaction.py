from fastapi import APIRouter, Depends, HTTPException, status 
from sqlalchemy.ext.asyncio import AsyncSession 
from sqlalchemy.exc import IntegrityError 
from app.database import get_db 

def get_transaction_router(create_transaction):
    router = APIRouter()

    @router.post("/transaction", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
    async def create_transaction_endpoint(data: TransactionCreate, db: AsyncSession = Depends(get_db)):
        try:
            transaction_response = await create_transaction(db, data)
            if transaction_response.idempotency_key == data.idempotency_key:
                return transaction_response  # New transaction created
            else:
                return transaction_response  # Duplicate transaction found
        except IntegrityError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return router 


