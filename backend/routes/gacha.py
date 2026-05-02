"""
ガチャルート
ガチャ実行APIエンドポイント
確率に基づいてカードを抽選し、コインを消費する
"""
import random
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user

router = APIRouter(prefix="/api/gacha", tags=["ガチャ"])

# レアリティの基本確率定義（合計100%）
RARITY_PROBABILITIES = {
    "UR": 0.01,   # 1%
    "SSR": 0.04,  # 4%
    "SR": 0.15,   # 15%
    "R": 0.30,    # 30%
    "N": 0.50,    # 50%
}


def draw_card(cards: list) -> models.Card:
    """
    カードリストから確率に基づいて1枚を抽選する
    各カードの設定確率を使って重み付き抽選を実施
    """
    if not cards:
        raise ValueError("カードリストが空です")

    # 重み付きランダム選択
    weights = [card.probability for card in cards]
    selected = random.choices(cards, weights=weights, k=1)[0]
    return selected


@router.post("/draw", response_model=schemas.GachaResultResponse)
def draw_gacha(
    request: schemas.GachaRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ガチャを1回実行する
    - コインを消費してパックからカードを1枚抽選
    - 在庫を1減らす
    - 結果をDBに記録する
    """
    # パック取得（在庫チェック含む）
    pack = db.query(models.Pack).filter(
        models.Pack.id == request.pack_id,
        models.Pack.is_active == True
    ).first()

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたパックが見つかりません"
        )

    # 在庫チェック
    if pack.stock <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このパックは売り切れです"
        )

    # コイン残高チェック
    if current_user.coin_balance < pack.price_coins:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"コインが不足しています（必要: {pack.price_coins}コイン、残高: {current_user.coin_balance}コイン）"
        )

    # パックのカードリスト取得
    cards = db.query(models.Card).filter(
        models.Card.pack_id == pack.id
    ).all()

    if not cards:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="パックにカードが設定されていません"
        )

    # カード抽選
    drawn_card = draw_card(cards)

    # コインを消費
    current_user.coin_balance -= pack.price_coins

    # 在庫を減らす
    pack.stock -= 1

    # ガチャ結果を記録
    gacha_result = models.GachaResult(
        user_id=current_user.id,
        pack_id=pack.id,
        card_id=drawn_card.id,
        coins_spent=pack.price_coins
    )
    db.add(gacha_result)

    # コイン消費履歴を記録
    coin_transaction = models.CoinTransaction(
        user_id=current_user.id,
        amount=-pack.price_coins,
        transaction_type="gacha",
        description=f"{pack.name}のガチャを実行"
    )
    db.add(coin_transaction)

    db.commit()
    db.refresh(current_user)
    db.refresh(pack)

    return schemas.GachaResultResponse(
        card=drawn_card,
        coins_spent=pack.price_coins,
        remaining_balance=current_user.coin_balance,
        pack_remaining_stock=pack.stock
    )


@router.get("/history")
def get_gacha_history(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ログインユーザーのガチャ履歴を取得する（最新20件）
    """
    results = db.query(models.GachaResult).filter(
        models.GachaResult.user_id == current_user.id
    ).order_by(models.GachaResult.created_at.desc()).limit(20).all()

    history = []
    for result in results:
        history.append({
            "id": result.id,
            "pack_name": result.pack.name,
            "card_name": result.card.name,
            "card_rarity": result.card.rarity,
            "card_image_url": result.card.image_url,
            "coins_spent": result.coins_spent,
            "created_at": result.created_at.isoformat()
        })

    return history
