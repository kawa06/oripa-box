"""
ガチャルート
ガチャ実行APIエンドポイント
確率に基づいてカードを抽選し、コインを消費する
天井（ピティ）システム: 50回引いたらA賞確定
"""
import random
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user

router = APIRouter(prefix="/api/gacha", tags=["ガチャ"])

# 天井回数（この回数引いたらA賞確定）
PITY_LIMIT = 50

# 賞の基本確率定義（合計100%）
RARITY_PROBABILITIES = {
    "A賞": 0.01,   # 1%
    "B賞": 0.04,   # 4%
    "C賞": 0.15,   # 15%
    "D賞": 0.30,   # 30%
    "E賞": 0.50,   # 50%
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


def draw_ur_card(cards: list) -> models.Card:
    """
    A賞カードのみから抽選する（天井発動時）
    A賞カードが存在しない場合は最高賞から抽選
    """
    a_cards = [c for c in cards if c.rarity == "A賞"]
    if a_cards:
        return random.choice(a_cards)
    # A賞が無い場合は B賞 から抽選
    b_cards = [c for c in cards if c.rarity == "B賞"]
    if b_cards:
        return random.choice(b_cards)
    # それも無い場合は通常抽選
    return draw_card(cards)


def get_or_create_pity(db: Session, user_id: int, pack_id: int) -> models.PityCounter:
    """天井カウンターを取得する。存在しない場合は新規作成する"""
    pity = db.query(models.PityCounter).filter(
        models.PityCounter.user_id == user_id,
        models.PityCounter.pack_id == pack_id
    ).first()

    if not pity:
        pity = models.PityCounter(user_id=user_id, pack_id=pack_id, count=0)
        db.add(pity)
        db.flush()

    return pity


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
    - 天井システム: 50回でA賞確定、A賞排出でカウンターリセット
    - コレクションに追加（UserCard テーブル）
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

    # 天井カウンター取得
    pity = get_or_create_pity(db, current_user.id, pack.id)
    pity_triggered = False

    # 天井発動チェック（PITY_LIMIT回に達したらA賞確定）
    if pity.count >= PITY_LIMIT - 1:
        drawn_card = draw_ur_card(cards)
        pity_triggered = True
    else:
        drawn_card = draw_card(cards)

    # A賞排出時は天井カウンターをリセット
    if drawn_card.rarity == "A賞":
        pity.count = 0
    else:
        pity.count += 1

    pity.updated_at = datetime.utcnow()

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

    # コレクション（UserCard）に追加
    existing_uc = db.query(models.UserCard).filter(
        models.UserCard.user_id == current_user.id,
        models.UserCard.card_id == drawn_card.id
    ).first()

    if existing_uc:
        existing_uc.count += 1
    else:
        db.add(models.UserCard(
            user_id=current_user.id,
            card_id=drawn_card.id,
            count=1
        ))

    db.commit()
    db.refresh(current_user)
    db.refresh(pack)
    db.refresh(pity)

    return schemas.GachaResultResponse(
        card=drawn_card,
        coins_spent=pack.price_coins,
        remaining_balance=current_user.coin_balance,
        pack_remaining_stock=pack.stock,
        pity_count=pity.count,
        pity_triggered=pity_triggered
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


@router.get("/pity/{pack_id}")
def get_pity_count(
    pack_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    指定パックの天井カウンターを返す
    """
    pity = db.query(models.PityCounter).filter(
        models.PityCounter.user_id == current_user.id,
        models.PityCounter.pack_id == pack_id
    ).first()

    count = pity.count if pity else 0
    return {
        "pack_id": pack_id,
        "pity_count": count,
        "pity_limit": PITY_LIMIT,
        "remaining_until_pity": PITY_LIMIT - count
    }
