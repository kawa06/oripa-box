"""
コレクションルート
ユーザーが所持しているカード一覧、コイン変換、発送申請を扱うAPIエンドポイント
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user

router = APIRouter(prefix="/api/collection", tags=["コレクション"])

# コイン変換レート（賞ごとのコイン数）
COIN_RATES = {
    "A賞": 1000,
    "B賞": 300,
    "C賞": 100,
    "D賞": 30,
    "E賞": 10,
}


@router.get("")
def get_collection(
    rarity: Optional[str] = Query(None, description="賞でフィルタ (A賞/B賞/C賞/D賞/E賞)"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ログインユーザーの所持カード一覧を取得する
    rarity パラメータで賞別フィルタが可能
    """
    query = db.query(models.UserCard).filter(
        models.UserCard.user_id == current_user.id
    )

    # 賞フィルタ（A賞〜E賞の文字列で一致）
    if rarity:
        query = query.join(models.Card).filter(models.Card.rarity == rarity)

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
            "status": uc.status,
            "obtained_at": uc.obtained_at.isoformat(),
            # コイン変換時の獲得コイン数（フロントエンド表示用）
            "coin_value": COIN_RATES.get(uc.card.rarity, 10),
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

    stats = {"A賞": 0, "B賞": 0, "C賞": 0, "D賞": 0, "E賞": 0, "total": 0}
    for uc in user_cards:
        rarity = uc.card.rarity
        if rarity in stats:
            stats[rarity] += uc.count
        stats["total"] += uc.count

    return stats


@router.post("/convert")
def convert_to_coins(
    request: schemas.ConvertToCoinsRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    指定カードをコインに変換する
    変換レート: E賞=10コイン, D賞=30コイン, C賞=100コイン, B賞=300コイン, A賞=1000コイン
    """
    # ユーザーのカードを検索
    user_card = db.query(models.UserCard).filter(
        models.UserCard.id == request.user_card_id,
        models.UserCard.user_id == current_user.id
    ).first()

    if not user_card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="カードが見つかりません")

    # 発送申請中・発送済みのカードは変換不可
    if user_card.status != "owned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このカードは現在変換できません（発送申請中または発送済み）"
        )

    # コイン変換レートを取得
    rarity = user_card.card.rarity
    coins = COIN_RATES.get(rarity, 10)

    # コインを付与
    current_user.coin_balance += coins

    # CoinTransaction に記録
    db.add(models.CoinTransaction(
        user_id=current_user.id,
        amount=coins,
        transaction_type="card_convert",
        description=f"{user_card.card.name}（{rarity}）をコインに変換"
    ))

    # 枚数が1枚の場合はレコード削除、複数の場合は枚数を減らす
    if user_card.count <= 1:
        db.delete(user_card)
    else:
        user_card.count -= 1

    db.commit()
    db.refresh(current_user)

    return {
        "message": f"{user_card.card.name} を {coins} コインに変換しました",
        "coins_received": coins,
        "new_balance": current_user.coin_balance
    }


@router.get("/address")
def get_shipping_address(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    ユーザーの保存済み発送先住所を取得する（最新1件）
    """
    address = db.query(models.ShippingAddress).filter(
        models.ShippingAddress.user_id == current_user.id
    ).order_by(models.ShippingAddress.updated_at.desc()).first()

    if not address:
        return None

    return {
        "id": address.id,
        "name": address.name,
        "postal_code": address.postal_code,
        "prefecture": address.prefecture,
        "city": address.city,
        "address": address.address,
        "building": address.building,
        "phone": address.phone,
    }


@router.post("/address")
def save_shipping_address(
    data: schemas.ShippingAddressCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    発送先住所を保存する（既存があれば上書き更新、なければ新規作成）
    """
    existing = db.query(models.ShippingAddress).filter(
        models.ShippingAddress.user_id == current_user.id
    ).order_by(models.ShippingAddress.updated_at.desc()).first()

    if existing:
        # 既存住所を更新
        existing.name = data.name
        existing.postal_code = data.postal_code
        existing.prefecture = data.prefecture
        existing.city = data.city
        existing.address = data.address
        existing.building = data.building
        existing.phone = data.phone
        db.commit()
        db.refresh(existing)
        return {
            "id": existing.id,
            "name": existing.name,
            "postal_code": existing.postal_code,
            "prefecture": existing.prefecture,
            "city": existing.city,
            "address": existing.address,
            "building": existing.building,
            "phone": existing.phone,
        }
    else:
        # 新規住所を作成
        address = models.ShippingAddress(
            user_id=current_user.id,
            name=data.name,
            postal_code=data.postal_code,
            prefecture=data.prefecture,
            city=data.city,
            address=data.address,
            building=data.building,
            phone=data.phone,
        )
        db.add(address)
        db.commit()
        db.refresh(address)
        return {
            "id": address.id,
            "name": address.name,
            "postal_code": address.postal_code,
            "prefecture": address.prefecture,
            "city": address.city,
            "address": address.address,
            "building": address.building,
            "phone": address.phone,
        }


@router.post("/ship")
def request_shipping(
    request: schemas.ShippingRequestCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    カードの発送申請を行う
    申請後はカードのステータスが「発送申請中」に変更される
    """
    # ユーザーのカードを検索
    user_card = db.query(models.UserCard).filter(
        models.UserCard.id == request.user_card_id,
        models.UserCard.user_id == current_user.id
    ).first()

    if not user_card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="カードが見つかりません")

    # 既に申請済みのカードは再申請不可
    if user_card.status != "owned":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このカードはすでに発送申請済みまたは発送済みです"
        )

    # 住所の存在チェック
    address = db.query(models.ShippingAddress).filter(
        models.ShippingAddress.id == request.address_id,
        models.ShippingAddress.user_id == current_user.id
    ).first()

    if not address:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="住所が見つかりません")

    # 発送申請を作成
    shipping_req = models.ShippingRequest(
        user_id=current_user.id,
        user_card_id=request.user_card_id,
        address_id=request.address_id,
        status="pending"
    )
    db.add(shipping_req)

    # カードのステータスを「発送申請中」に変更
    user_card.status = "shipping_requested"

    db.commit()
    db.refresh(shipping_req)

    return {
        "message": f"{user_card.card.name} の発送申請を受け付けました",
        "shipping_request_id": shipping_req.id,
        "status": "pending"
    }
