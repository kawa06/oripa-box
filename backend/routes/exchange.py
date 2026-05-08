"""
ポイント交換ルート
被りカードをポイントに変換し、ポイントでカードを入手できるシステム
レアリティ別変換レート: N=10pt, R=30pt, SR=100pt, SSR=300pt, UR=1000pt
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user

router = APIRouter(prefix="/api/exchange", tags=["ポイント交換"])

# レアリティ別ポイント変換レート
RARITY_POINTS = {
    "N": 10,
    "R": 30,
    "SR": 100,
    "SSR": 300,
    "UR": 1000,
}

# ポイントでカードを入手する際のポイントコスト（変換レートの2倍）
RARITY_EXCHANGE_COST = {
    "N": 20,
    "R": 60,
    "SR": 200,
    "SSR": 600,
    "UR": 2000,
}


@router.get("/point-balance", response_model=schemas.PointBalanceResponse)
def get_point_balance(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ログインユーザーのポイント残高を返す"""
    return {"points": current_user.points}


@router.post("/convert")
def convert_card_to_points(
    request: schemas.ExchangeRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    所持カードをポイントに変換する
    user_card_id: 変換するユーザー所持カードID
    """
    user_card = db.query(models.UserCard).filter(
        models.UserCard.id == request.user_card_id,
        models.UserCard.user_id == current_user.id
    ).first()

    if not user_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="所持カードが見つかりません"
        )

    card = user_card.card
    rarity = card.rarity
    earned_points = RARITY_POINTS.get(rarity, 10)

    # 所持枚数を1減らす（0になれば削除）
    if user_card.count > 1:
        user_card.count -= 1
    else:
        db.delete(user_card)

    # ポイント付与
    current_user.points += earned_points
    db.commit()
    db.refresh(current_user)

    return {
        "message": f"「{card.name}」({rarity}) を {earned_points} ポイントに変換しました",
        "earned_points": earned_points,
        "total_points": current_user.points
    }


@router.get("/available-cards")
def get_available_exchange_cards(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ポイントで交換可能なカード一覧を返す
    （全パックの全カードが対象）
    """
    cards = db.query(models.Card).all()
    result = []
    for card in cards:
        cost = RARITY_EXCHANGE_COST.get(card.rarity, 20)
        result.append({
            "id": card.id,
            "name": card.name,
            "rarity": card.rarity,
            "image_url": card.image_url,
            "description": card.description,
            "pack_name": card.pack.name,
            "pack_id": card.pack_id,
            "exchange_cost": cost,
            "can_afford": current_user.points >= cost
        })
    return result


@router.post("/get-card")
def exchange_card(
    request: schemas.ExchangeCardRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ポイントを消費して指定カードを入手する
    """
    card = db.query(models.Card).filter(models.Card.id == request.card_id).first()
    if not card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="カードが見つかりません"
        )

    cost = RARITY_EXCHANGE_COST.get(card.rarity, 20)
    if current_user.points < cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ポイントが不足しています（必要: {cost}pt、残高: {current_user.points}pt）"
        )

    # ポイント消費
    current_user.points -= cost

    # コレクションに追加（既に持っていれば枚数+1）
    existing = db.query(models.UserCard).filter(
        models.UserCard.user_id == current_user.id,
        models.UserCard.card_id == card.id
    ).first()

    if existing:
        existing.count += 1
    else:
        db.add(models.UserCard(
            user_id=current_user.id,
            card_id=card.id,
            count=1
        ))

    db.commit()
    db.refresh(current_user)

    return {
        "message": f"「{card.name}」({card.rarity}) を入手しました！",
        "card_name": card.name,
        "card_rarity": card.rarity,
        "card_image_url": card.image_url,
        "spent_points": cost,
        "remaining_points": current_user.points
    }
