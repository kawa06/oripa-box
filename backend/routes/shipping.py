"""
発送管理ルート
管理者が発送申請の一覧確認・ステータス更新を行うAPIエンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user

router = APIRouter(prefix="/api/admin/shipping", tags=["発送管理"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    """管理者権限チェック用依存性注入"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です"
        )
    return current_user


@router.get("")
def list_shipping_requests(
    status_filter: str = None,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    発送申請一覧を取得する（管理者専用）
    status_filter: pending/shipped/completed でフィルタ可能
    """
    query = db.query(models.ShippingRequest)

    if status_filter:
        query = query.filter(models.ShippingRequest.status == status_filter)

    # 新しい順に並べる
    requests = query.order_by(models.ShippingRequest.created_at.desc()).all()

    result = []
    for req in requests:
        result.append({
            "id": req.id,
            "status": req.status,
            "created_at": req.created_at.isoformat(),
            "updated_at": req.updated_at.isoformat(),
            # ユーザー情報
            "username": req.user.username,
            "user_email": req.user.email,
            # カード情報
            "card_name": req.user_card.card.name,
            "card_rarity": req.user_card.card.rarity,
            "pack_name": req.user_card.card.pack.name,
            "user_card_id": req.user_card_id,
            # 住所情報
            "address_name": req.address.name,
            "postal_code": req.address.postal_code,
            "prefecture": req.address.prefecture,
            "city": req.address.city,
            "address": req.address.address,
            "building": req.address.building,
            "phone": req.address.phone,
        })

    return result


@router.put("/{request_id}")
def update_shipping_status(
    request_id: int,
    update: schemas.ShippingStatusUpdate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    発送申請のステータスを更新する（管理者専用）
    ステータス遷移: pending（発送待ち）→ shipped（発送済み）→ completed（完了）
    """
    # 有効なステータス値のチェック
    valid_statuses = ["pending", "shipped", "completed"]
    if update.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"無効なステータスです。有効な値: {', '.join(valid_statuses)}"
        )

    req = db.query(models.ShippingRequest).filter(
        models.ShippingRequest.id == request_id
    ).first()

    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="発送申請が見つかりません")

    old_status = req.status
    req.status = update.status

    # UserCard のステータスも連動して更新する
    user_card = req.user_card
    if update.status == "shipped":
        user_card.status = "shipped"
    elif update.status == "completed":
        user_card.status = "shipped"  # 完了後もshippedのまま
    elif update.status == "pending":
        # 差し戻しの場合は申請中に戻す
        user_card.status = "shipping_requested"

    db.commit()

    status_labels = {
        "pending": "発送待ち",
        "shipped": "発送済み",
        "completed": "完了"
    }

    return {
        "message": f"発送申請 #{request_id} のステータスを「{status_labels.get(update.status, update.status)}」に更新しました",
        "id": req.id,
        "status": req.status,
        "old_status": old_status
    }
