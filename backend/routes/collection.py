"""
コレクションルート
ユーザーが所持しているカード一覧を返すAPIエンドポイント
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models
from backend.auth import get_current_user

router = APIRouter(prefix="/api/collection", tags=["コレクション"])


@router.get("")
def get_collection(
    rarity: Optional[str] = Query(None, description="レアリティでフィルタ (UR/SSR/SR/R/N)"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ログインユーザーの所持カード一覧を取得する
    rarity パラメータでレアリティ別フィルタが可能
    """
    query = db.query(models.UserCard).filter(
        models.UserCard.user_id == current_user.id
    )

    # レアリティフィルタ
    if rarity:
        query = query.join(models.Card).filter(models.Card.rarity == rarity.upper())

    user_cards = query.order_by(
        models.UserCard.obtained_at.desc()
    ).all()

    result = []
    for uc in user_cards:
        result.append({
            "id": uc.id,
            "card_id": uc.card_id,
            "card_name": uc.card.name,
            "card_rarity": uc.card.rarity,
            "card_image_url": uc.card.image_url,
            "card_description": uc.card.description,
            "pack_name": uc.card.pack.name,
            "pack_id": uc.card.pack_id,
            "count": uc.count,
            "obtained_at": uc.obtained_at.isoformat()
        })

    return result


@router.get("/stats")
def get_collection_stats(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ユーザーのコレクション統計を返す（レアリティ別枚数）
    """
    user_cards = db.query(models.UserCard).filter(
        models.UserCard.user_id == current_user.id
    ).all()

    stats = {"UR": 0, "SSR": 0, "SR": 0, "R": 0, "N": 0, "total": 0}
    for uc in user_cards:
        rarity = uc.card.rarity
        if rarity in stats:
            stats[rarity] += uc.count
        stats["total"] += uc.count

    return stats
