"""
管理者ルート
管理者専用のAPIエンドポイント（パック・カード・ユーザー・在庫管理）
is_admin フラグで管理者かどうかを判定する
"""
from typing import List
import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user

router = APIRouter(prefix="/api/admin", tags=["管理者"])


def require_admin(current_user: models.User = Depends(get_current_user)):
    """管理者権限チェック用依存性注入"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です"
        )
    return current_user


# ===== ユーザー管理 =====

@router.get("/users", response_model=List[schemas.AdminUserResponse])
def list_users(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """全ユーザー一覧を取得する"""
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    return users


@router.post("/users/grant-coins")
def grant_coins(
    request: schemas.AdminGrantCoinsRequest,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """指定ユーザーにコインを付与する"""
    user = db.query(models.User).filter(models.User.id == request.user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ユーザーが見つかりません")

    user.coin_balance += request.amount
    db.add(models.CoinTransaction(
        user_id=user.id,
        amount=request.amount,
        transaction_type="bonus",
        description=request.description or "管理者によるコイン付与"
    ))
    db.commit()
    db.refresh(user)
    return {"message": f"{user.username} に {request.amount} コインを付与しました", "new_balance": user.coin_balance}


# ===== パック管理 =====

@router.get("/packs", response_model=List[schemas.PackResponse])
def list_all_packs(
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """全パック一覧（非アクティブ含む）を取得する"""
    packs = db.query(models.Pack).order_by(models.Pack.created_at.desc()).all()
    return packs


@router.post("/packs", response_model=schemas.PackListResponse)
def create_pack(
    pack_data: schemas.AdminPackCreate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """新しいパックを作成する"""
    pack = models.Pack(**pack_data.dict())
    db.add(pack)
    db.commit()
    db.refresh(pack)
    return pack


@router.put("/packs/{pack_id}", response_model=schemas.PackListResponse)
def update_pack(
    pack_id: int,
    pack_data: schemas.AdminPackUpdate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """パック情報を更新する"""
    pack = db.query(models.Pack).filter(models.Pack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="パックが見つかりません")

    # Noneでないフィールドのみ更新
    update_data = pack_data.dict(exclude_none=True)
    for key, value in update_data.items():
        setattr(pack, key, value)

    db.commit()
    db.refresh(pack)
    return pack


@router.delete("/packs/{pack_id}")
def delete_pack(
    pack_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """パックを削除（論理削除: is_active=False）する"""
    pack = db.query(models.Pack).filter(models.Pack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="パックが見つかりません")

    pack.is_active = False
    db.commit()
    return {"message": f"パック '{pack.name}' を無効化しました"}


@router.post("/packs/{pack_id}/reset-stock")
def reset_pack_stock(
    pack_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """パックの在庫を最大値にリセットする"""
    pack = db.query(models.Pack).filter(models.Pack.id == pack_id).first()
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="パックが見つかりません")

    pack.stock = pack.max_stock
    db.commit()
    db.refresh(pack)
    return {"message": f"'{pack.name}' の在庫を {pack.max_stock} にリセットしました", "stock": pack.stock}


# ===== カード管理 =====

@router.get("/cards")
def list_all_cards(
    pack_id: int = None,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """全カード一覧を取得する（pack_idでフィルタ可能）"""
    query = db.query(models.Card)
    if pack_id:
        query = query.filter(models.Card.pack_id == pack_id)
    cards = query.order_by(models.Card.pack_id, models.Card.rarity).all()

    result = []
    for card in cards:
        result.append({
            "id": card.id,
            "pack_id": card.pack_id,
            "pack_name": card.pack.name,
            "name": card.name,
            "rarity": card.rarity,
            "probability": card.probability,
            "image_url": card.image_url,
            "description": card.description,
            # カード固有のコイン変換レート（Noneの場合は賞別デフォルト値を使用）
            "coin_value": card.coin_value,
        })
    return result


@router.post("/cards", response_model=schemas.CardResponse)
def create_card(
    card_data: schemas.AdminCardCreate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """新しいカードを作成する"""
    # パック存在チェック
    pack = db.query(models.Pack).filter(models.Pack.id == card_data.pack_id).first()
    if not pack:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="パックが見つかりません")

    card = models.Card(**card_data.dict())
    db.add(card)
    db.commit()
    db.refresh(card)
    return card


@router.put("/cards/{card_id}", response_model=schemas.CardResponse)
def update_card(
    card_id: int,
    card_data: schemas.AdminCardUpdate,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """カード情報を更新する"""
    card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="カードが見つかりません")

    # Noneでないフィールドのみ更新（coin_value は明示的にNullを許可するため別途処理）
    update_data = card_data.dict(exclude_none=True)
    for key, value in update_data.items():
        setattr(card, key, value)

    # coin_value はリクエストに明示的に含まれていればNullも許可（レート削除対応）
    if "coin_value" in card_data.dict(exclude_unset=False) and card_data.coin_value is None:
        # リクエストに coin_value=null が含まれている場合はデフォルト値使用に戻す
        card.coin_value = None

    db.commit()
    db.refresh(card)
    return card


@router.delete("/cards/{card_id}")
def delete_card(
    card_id: int,
    admin: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """カードを削除する"""
    card = db.query(models.Card).filter(models.Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="カードが見つかりません")

    db.delete(card)
    db.commit()
    return {"message": f"カード '{card.name}' を削除しました"}


# ===== 画像アップロード =====

# 対応する画像拡張子
_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
# ファイルサイズ上限: 5MB
_MAX_FILE_SIZE = 5 * 1024 * 1024
# アップロード先ディレクトリ（プロジェクトルート基準）
_UPLOAD_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "backend", "static", "uploads"
)


@router.post("/upload")
async def upload_image(
    file: UploadFile = File(...),
    admin: models.User = Depends(require_admin)
):
    """
    画像ファイルをアップロードしてサーバーに保存する
    対応形式: jpg, jpeg, png, gif, webp
    最大サイズ: 5MB
    保存先: backend/static/uploads/
    レスポンス: {"url": "/static/uploads/filename.ext"}
    """
    # 拡張子チェック
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"対応していないファイル形式です。対応形式: {', '.join(_ALLOWED_EXTENSIONS)}"
        )

    # ファイル内容を読み込み
    content = await file.read()

    # サイズチェック
    if len(content) > _MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ファイルサイズが5MBを超えています"
        )

    # アップロードディレクトリを作成（存在しなければ）
    os.makedirs(_UPLOAD_DIR, exist_ok=True)

    # ユニークなファイル名を生成してサーバーに保存
    unique_name = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(_UPLOAD_DIR, unique_name)

    with open(save_path, "wb") as f:
        f.write(content)

    # アクセスURLを返す
    return {"url": f"/static/uploads/{unique_name}"}
