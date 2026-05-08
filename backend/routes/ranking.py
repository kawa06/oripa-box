"""
ランキングルート
URカード保有数ランキングを返すAPIエンドポイント
"""
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.database import get_db
from backend import models, schemas

router = APIRouter(prefix="/api/ranking", tags=["ランキング"])


@router.get("/ur", response_model=List[schemas.RankingEntry])
def get_ur_ranking(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    URカード保有数ランキングを返す（上位20名）
    UserCard テーブルの UR カード所持枚数合計で順位付け
    """
    # UR カードのIDを取得
    ur_card_ids = db.query(models.Card.id).filter(
        models.Card.rarity == "UR"
    ).subquery()

    # ユーザーごとの UR 所持枚数合計を集計
    ranking_query = (
        db.query(
            models.User.username,
            func.coalesce(func.sum(models.UserCard.count), 0).label("ur_count")
        )
        .outerjoin(
            models.UserCard,
            (models.UserCard.user_id == models.User.id) &
            (models.UserCard.card_id.in_(ur_card_ids))
        )
        .filter(models.User.is_active == True)
        .group_by(models.User.id, models.User.username)
        .order_by(func.coalesce(func.sum(models.UserCard.count), 0).desc())
        .limit(limit)
        .all()
    )

    result = []
    for rank, (username, ur_count) in enumerate(ranking_query, start=1):
        result.append(schemas.RankingEntry(
            rank=rank,
            username=username,
            ur_count=int(ur_count)
        ))

    return result
