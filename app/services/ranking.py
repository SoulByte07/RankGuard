from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio.session import AsyncSession
def rankFormula(total_earned, total_spent, transaction_count, bonus_count, days_since_last_activity):
   score: flaot = (total_earned * 1.0)
           + (total_spent * 0.5)
           + (transaction_count * 10)
           + (bonus_count * 50)
           - (days_since_last_activity * 0.1)   # age penalty
   return score

async def compute_rankings(db:AsyncSession):
    """
  - Read all `user_snapshots`, compute score for each
  - Assign rank (ORDER BY score DESC, last_activity ASC)
  - Upsert into `rankings` table (or refresh materialised view)
  """
    result = await db.execute(text("SELECT * FROM user_snapshots"))
    user_snapshots = result.fetchall()
    for snapshot in user_snapshots:
        user_id = snapshot[0]
        total_earned = snapshot[1]
        total_spent = snapshot[2]
        transaction_count = snapshot[3]
        bonus_count = snapshot[4]
        days_since_last_activity = snapshot[5]
        score = rankFormula(total_earned, total_spent, transaction_count, bonus_count, days_since_last_activity)
        await db.execute(text("INSERT INTO rankings (user_id, score) VALUES (:user_id, :score) ON CONFLICT (user_id) DO UPDATE SET score = :score"))
        await db.commit()

"""
  - Read from `rankings` table ordered by rank
  - Join `user_snapshots` for display fields
"""
async def get_rankings(db: AsyncSession):
    result = await db.execute(text("SELECT * FROM rankings ORDER BY score DESC"))
    rankings = result.fetchall()
    return rankings

async def get_user_snapshot(db: AsyncSession, user_id: int):
    result = await db.execute(text("SELECT * FROM user_snapshots WHERE user_id = :user_id"))
    snapshot = result.fetchone()
    return snapshot
