"""
パック一覧ルート
販売中のガチャパック情報を返すAPIエンドポイント
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user

router = APIRouter(prefix="/api/packs", tags=["パック"])


@router.get("/", response_model=List[schemas.PackListResponse])
def get_packs(db: Session = Depends(get_db)):
    """
    販売中のパック一覧を取得する（認証不要）
    """
    packs = db.query(models.Pack).filter(models.Pack.is_active == True).all()
    return packs


@router.get("/{pack_id}", response_model=schemas.PackResponse)
def get_pack(pack_id: int, db: Session = Depends(get_db)):
    """
    指定したパックの詳細情報（カードリスト含む）を取得する
    """
    pack = db.query(models.Pack).filter(
        models.Pack.id == pack_id,
        models.Pack.is_active == True
    ).first()

    if not pack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="指定されたパックが見つかりません"
        )

    return pack
