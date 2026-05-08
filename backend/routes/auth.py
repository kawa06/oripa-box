"""
認証ルート
ユーザー登録・ログインAPIエンドポイント
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, status
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user
)
from backend.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES, ADMIN_EMAIL,
    SECRET_KEY, ALGORITHM, SMTP_ENABLED
)
from backend.email_utils import send_verification_email

router = APIRouter(prefix="/api/auth", tags=["認証"])


@router.post("/register")
def register(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    新規ユーザー登録
    メールアドレスとユーザー名の重複チェック後、アカウントを作成する
    登録後は確認メールを送信し、メール認証完了まではログイン不可
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
    # ADMIN_EMAILと一致した場合は管理者アカウントとして作成
    is_admin = bool(ADMIN_EMAIL and user_data.email.lower() == ADMIN_EMAIL.lower())
    # 管理者アカウント、またはSMTP未設定環境ではメール認証をスキップして最初から認証済みにする
    is_verified_initial = is_admin or not SMTP_ENABLED
    new_user = models.User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hashed_password,
        coin_balance=0,
        is_admin=is_admin,
        is_verified=is_verified_initial
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

    # 認証メールを送信（SMTP未設定の場合は自動スキップ）
    email_sent = send_verification_email(
        to_email=new_user.email,
        username=new_user.username,
        user_id=new_user.id
    )

    # 登録成功レスポンス（トークンは返さず、メール確認を促す）
    return {
        "message": "登録が完了しました。確認メールを送信しました。メールを確認してください。",
        "email_sent": email_sent,
        "email": new_user.email,
        # SMTP未設定の開発環境向け: 認証済みなら即トークンを返す
        "requires_verification": not is_verified_initial and email_sent,
        # 管理者またはSMTP未設定の場合はトークンを即返す（開発利便性）
        "access_token": (
            create_access_token(
                data={"sub": str(new_user.id)},
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            ) if (is_verified_initial or not email_sent) else None
        ),
        "token_type": "bearer",
        "user": schemas.UserResponse.from_orm(new_user) if (is_verified_initial or not email_sent) else None
    }


@router.post("/login", response_model=schemas.Token)
def login(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    ログイン
    メールアドレスとパスワードを検証してJWTトークンを返す
    メール認証未完了ユーザーはログイン不可
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

    # メール認証チェック（SMTP設定済みの場合のみ実施）
    if SMTP_ENABLED and not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="メール認証が完了していません。登録時に送信されたメールを確認してください。"
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


@router.get("/verify")
def verify_email(token: str = Query(...), db: Session = Depends(get_db)):
    """
    メールアドレス認証エンドポイント
    メール内のリンクからアクセスされ、トークンを検証してアカウントを有効化する
    """
    invalid_exception = HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="認証リンクが無効または期限切れです"
    )

    try:
        # JWTトークンをデコード
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")

        # トークンタイプチェック（メール認証専用トークンのみ受け付ける）
        if token_type != "email_verify" or user_id is None:
            raise invalid_exception

    except JWTError:
        raise invalid_exception

    # ユーザー検索
    user = db.query(models.User).filter(models.User.id == int(user_id)).first()
    if not user:
        raise invalid_exception

    # すでに認証済みの場合
    if user.is_verified:
        return {"message": "メールアドレスはすでに認証済みです", "already_verified": True}

    # 認証済みに更新
    user.is_verified = True
    db.commit()
    db.refresh(user)

    # 認証成功後のJWTトークンを生成（自動ログイン用）
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )

    return {
        "message": "メールアドレスの認証が完了しました。ログインできます。",
        "access_token": access_token,
        "token_type": "bearer",
        "user": schemas.UserResponse.from_orm(user)
    }


@router.post("/resend-verification")
def resend_verification(credentials: schemas.UserLogin, db: Session = Depends(get_db)):
    """
    認証メールを再送信するエンドポイント
    パスワードを確認したうえで認証メールを再送する
    """
    # ユーザー検索・パスワード照合
    user = db.query(models.User).filter(
        models.User.email == credentials.email
    ).first()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="メールアドレスまたはパスワードが正しくありません"
        )

    if user.is_verified:
        return {"message": "メールアドレスはすでに認証済みです"}

    # 認証メールを再送信
    email_sent = send_verification_email(
        to_email=user.email,
        username=user.username,
        user_id=user.id
    )

    if not email_sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="メール送信に失敗しました。しばらく後でお試しください。"
        )

    return {"message": "認証メールを再送信しました。メールをご確認ください。"}


@router.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    """
    現在ログイン中のユーザー情報を取得する
    """
    return current_user


class DeleteAccountRequest(BaseModel):
    """アカウント削除リクエスト（パスワード確認用）"""
    password: str


@router.delete("/delete-account")
def delete_account(
    request: DeleteAccountRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """
    ログイン中のユーザーのアカウントを物理削除する
    パスワードを確認してから、ユーザーに紐づく全データを削除する
    """
    # パスワード照合
    if not verify_password(request.password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="パスワードが正しくありません"
        )

    user_id = current_user.id

    # 関連データを順番に削除（外部キー制約に注意）
    db.query(models.PityCounter).filter(models.PityCounter.user_id == user_id).delete()
    db.query(models.UserCard).filter(models.UserCard.user_id == user_id).delete()
    db.query(models.CoinTransaction).filter(models.CoinTransaction.user_id == user_id).delete()
    db.query(models.GachaResult).filter(models.GachaResult.user_id == user_id).delete()

    # ユーザー本体を削除
    db.delete(current_user)
    db.commit()

    return {"message": "アカウントを削除しました"}
