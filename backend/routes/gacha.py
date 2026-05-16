"""
ガチャルート
ガチャ実行APIエンドポイント
確率に基づいてカードを抽選し、コインを消費する
天井（ピティ）システム: 50回引いたらA賞確定
パックごとにprobabilitiesフィールドで各賞の排出確率を設定可能
"""
import json
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

# デフォルト賞確率（パックにprobabilitiesが未設定の場合に使用、合計100%）
DEFAULT_RARITY_WEIGHTS = {
    "A賞": 1,   # 1%
    "B賞": 4,   # 4%
    "C賞": 15,  # 15%
    "D賞": 30,  # 30%
    "E賞": 50,  # 50%
}


def get_rarity_weights(pack: models.Pack) -> dict:
    """
    パックのprobabilitiesからレアリティ別重みを取得する。
    未設定の場合はデフォルト値を返す。
    """
    if pack.probabilities:
        try:
            weights = json.loads(pack.probabilities)
            # キーと値が正常かチェック
            if isinstance(weights, dict) and all(isinstance(v, (int, float)) for v in weights.values()):
                return weights
        except (json.JSONDecodeError, ValueError):
            pass
    # フォールバック: デフォルト確率を使用
    return DEFAULT_RARITY_WEIGHTS


def draw_card(cards: list, rarity_weights: dict) -> models.Card:
    """
    カードリストから賞ごとの確率に基づいて1枚を抽選する。
    まずrarity_weightsで賞を選び、その賞のカードから均等抽選する。
    """
    if not cards:
        raise ValueError("カードリストが空です")

    # カードを賞ごとにグループ化
    rarity_groups: dict[str, list] = {}
    for card in cards:
        rarity_groups.setdefault(card.rarity, []).append(card)

    # 存在する賞のみで重み付き賞選択
    available_rarities = [r for r in rarity_weights if r in rarity_groups]
    if not available_rarities:
        # フォールバック: 全カードから均等抽選
        return random.choice(cards)

    weights = [rarity_weights[r] for r in available_rarities]
    chosen_rarity = random.choices(available_rarities, weights=weights, k=1)[0]

    # 選ばれた賞のカードから均等抽選
    return random.choice(rarity_groups[chosen_rarity])


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


def _execute_single_draw(
    db: Session,
    pack: models.Pack,
    cards: list,
    rarity_weights: dict,
    pity: models.PityCounter,
    current_user: models.User
) -> tuple:
    """
    1回分のガチャ抽選ロジック（まとめ引きからも呼び出せる共通処理）
    戻り値: (drawn_card, pity_triggered)
    天井カウンターの更新・コイン消費・在庫減算・DB記録は呼び出し元で行う
    """
    pity_triggered = False

    # 天井発動チェック（PITY_LIMIT回に達したらA賞確定）
    if pity.count >= PITY_LIMIT - 1:
        drawn_card = draw_ur_card(cards)
        pity_triggered = True
    else:
        drawn_card = draw_card(cards, rarity_weights)

    # A賞排出時は天井カウンターをリセット
    if drawn_card.rarity == "A賞":
        pity.count = 0
    else:
        pity.count += 1

    return drawn_card, pity_triggered


@router.post("/draw", response_model=schemas.GachaResultResponse)
def draw_gacha(
    request: schemas.GachaRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ガチャを実行する（count=1 の場合は単発、10/100はまとめ引きへリダイレクト）
    - countが10または100の場合は /draw/multi エンドポイントと同等の処理を行う
    - 後方互換のため、count=1 の場合は従来どおり GachaResultResponse を返す
    """
    # まとめ引きの場合は専用エンドポイントへ委譲
    if request.count > 1:
        multi_result = draw_gacha_multi(request, current_user, db)
        # まとめ引き結果の最後のカードを1回引きレスポンス形式に変換して返す
        last = multi_result.cards[-1]
        return last

    # --- 以下は count=1 の通常1回引き処理 ---

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

    # パックの賞別確率を取得（未設定の場合はデフォルト）
    rarity_weights = get_rarity_weights(pack)

    # 抽選
    drawn_card, pity_triggered = _execute_single_draw(db, pack, cards, rarity_weights, pity, current_user)

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
        user_card_record = existing_uc
    else:
        user_card_record = models.UserCard(
            user_id=current_user.id,
            card_id=drawn_card.id,
            count=1
        )
        db.add(user_card_record)

    db.commit()
    db.refresh(current_user)
    db.refresh(pack)
    db.refresh(pity)
    db.refresh(user_card_record)

    return schemas.GachaResultResponse(
        card=drawn_card,
        user_card_id=user_card_record.id,
        coins_spent=pack.price_coins,
        remaining_balance=current_user.coin_balance,
        pack_remaining_stock=pack.stock,
        pity_count=pity.count,
        pity_triggered=pity_triggered
    )


@router.post("/draw/multi", response_model=schemas.MultiGachaResultResponse)
def draw_gacha_multi(
    request: schemas.GachaRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    まとめ引きガチャを実行する（10回 / 100回）
    - コイン消費: パック価格 × count
    - 在庫チェック: 残り在庫 >= count でなければエラー
    - 天井カウンターもcount分加算
    - 結果を配列で返す
    """
    count = request.count

    # 許可する枚数: 1, 10, 100
    if count not in (1, 10, 100):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="countは1、10、100のいずれかで指定してください"
        )

    # パック取得
    pack = db.query(models.Pack).filter(
        models.Pack.id == request.pack_id,
        models.Pack.is_active == True
    ).first()

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたパックが見つかりません"
        )

    # 在庫チェック（まとめ引き分の在庫が必要）
    if pack.stock < count:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"在庫が不足しています（必要: {count}口、残在庫: {pack.stock}口）"
        )

    # コイン残高チェック（まとめ引き分のコインが必要）
    total_cost = pack.price_coins * count
    if current_user.coin_balance < total_cost:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"コインが不足しています（必要: {total_cost}コイン、残高: {current_user.coin_balance}コイン）"
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

    # パックの賞別確率を取得
    rarity_weights = get_rarity_weights(pack)

    # ======== count回分のガチャを実行 ========
    results = []
    rarity_summary: dict[str, int] = {}

    for _ in range(count):
        drawn_card, pity_triggered = _execute_single_draw(db, pack, cards, rarity_weights, pity, current_user)

        # ガチャ結果をDBに記録
        gacha_result = models.GachaResult(
            user_id=current_user.id,
            pack_id=pack.id,
            card_id=drawn_card.id,
            coins_spent=pack.price_coins
        )
        db.add(gacha_result)

        # コレクション（UserCard）に追加
        existing_uc = db.query(models.UserCard).filter(
            models.UserCard.user_id == current_user.id,
            models.UserCard.card_id == drawn_card.id
        ).first()
        if existing_uc:
            existing_uc.count += 1
            uc_id = existing_uc.id
        else:
            new_uc = models.UserCard(
                user_id=current_user.id,
                card_id=drawn_card.id,
                count=1
            )
            db.add(new_uc)
            db.flush()  # IDを取得するためflush
            uc_id = new_uc.id

        # サマリー集計
        rarity_summary[drawn_card.rarity] = rarity_summary.get(drawn_card.rarity, 0) + 1

        # 各回の結果を格納（残高/在庫は後でまとめて更新）
        results.append({
            "card": drawn_card,
            "pity_triggered": pity_triggered,
            "user_card_id": uc_id,
        })

    # コインをまとめて消費
    current_user.coin_balance -= total_cost

    # 在庫をまとめて減算
    pack.stock -= count

    pity.updated_at = datetime.utcnow()

    # コイン消費履歴を1件まとめて記録
    coin_transaction = models.CoinTransaction(
        user_id=current_user.id,
        amount=-total_cost,
        transaction_type="gacha",
        description=f"{pack.name}のガチャを{count}回実行"
    )
    db.add(coin_transaction)

    db.commit()
    db.refresh(current_user)
    db.refresh(pack)
    db.refresh(pity)

    # レスポンス構築
    card_responses = [
        schemas.GachaResultResponse(
            card=r["card"],
            user_card_id=r["user_card_id"],
            coins_spent=pack.price_coins,
            remaining_balance=current_user.coin_balance,
            pack_remaining_stock=pack.stock,
            pity_count=pity.count,
            pity_triggered=r["pity_triggered"]
        )
        for r in results
    ]

    return schemas.MultiGachaResultResponse(
        cards=card_responses,
        total_coins_spent=total_cost,
        remaining_balance=current_user.coin_balance,
        pack_remaining_stock=pack.stock,
        pity_count=pity.count,
        count=count,
        rarity_summary=rarity_summary
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
