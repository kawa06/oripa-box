"""
認証ルート
ユーザー登録・ログインAPIエンドポイント
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from backend.config import ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/api/auth", tags=["認証"])


@router.post("/register", response_model=schemas.Token)
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    新規ユーザー登録
    メールアドレスとユーザー名の重複チェック後、アカウントを作成する
    """
    # メールアドレスの重複チェック
    existing_email = db.query(models.User).filter(
        models.User.email == user_data.email
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスはすでに登録されています"
        )

    # ユーザー名の重複チェック
    existing_username = db.query(models.User).filter(
        models.User.username == user_data.username
    ).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このユーザー名はすでに使用されています"
        )

    # パスワードバリデーション（最低6文字）
    if len(user_data.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="パスワードは6文字以上で設定してください"
        )

    # ユーザー作成
    hashed_password = get_password_hash(user_data.password)
    new_user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        coin_balance=0
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # 新規登録ボーナス（50コイン）を付与
    bonus_transaction = models.CoinTransaction(
        user_id=new_user.id,
        amount=50,
        transaction_type="bonus",
        description="新規登録ボーナス"
    )
    new_user.coin_balance += 50
    db.add(bonus_transaction)
    db.commit()
    db.refresh(new_user)

    # JWTトークン生成
    access_token = create_access_token(
        data={"sub": str(new_user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=new_user
    )


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    ログイン
    メールアドレスとパスワードを検証してJWTトークンを返す
    """
    # ユーザー検索
    user = db.query(models.User).filter(
        models.User.email == credentials.email
    ).first()

    # 認証失敗（セキュリティのためユーザー不存在とパスワード誤りを区別しない）
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="アカウントが無効です"
        )

    # JWTトークン生成
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return schemas.Token(
        access_token=access_token,
        token_type="bearer",
        user=user
    )


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """
    現在ログイン中のユーザー情報を取得する
    """
    return current_user
