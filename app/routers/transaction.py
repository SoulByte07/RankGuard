from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas import TransactionCreate, TransactionResponse
from app.services.transaction import create_transaction

router = APIRouter()


@router.post("/transaction", response_model=TransactionResponse)
async def create_transaction_endpoint(
    data: TransactionCreate,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        resp, is_created = await create_transaction(db, data)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Constraint violation"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )

    response.status_code = (
        status.HTTP_201_CREATED if is_created else status.HTTP_200_OK
    )
    return resp
