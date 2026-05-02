"""
コインルート
コイン残高確認・購入（Stripe連携）APIエンドポイント
"""
import stripe
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from backend.database import get_db
from backend import models, schemas
from backend.auth import get_current_user
from backend.config import (
    STRIPE_SECRET_KEY,
    STRIPE_WEBHOOK_SECRET,
    FRONTEND_URL,
    COIN_PACKS
)

# Stripe APIキー設定
stripe.api_key = STRIPE_SECRET_KEY

router = APIRouter(prefix="/api/coins", tags=["コイン"])


@router.get("/balance", response_model=schemas.CoinBalanceResponse)
def get_balance(current_user: models.User = Depends(get_current_user)):
    """
    現在のコイン残高を取得する
    """
    return schemas.CoinBalanceResponse(balance=current_user.coin_balance)


@router.get("/transactions", response_model=List[schemas.CoinTransactionResponse])
def get_transactions(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    コイン取引履歴を取得する（最新30件）
    """
    transactions = db.query(models.CoinTransaction).filter(
        models.CoinTransaction.user_id == current_user.id
    ).order_by(models.CoinTransaction.created_at.desc()).limit(30).all()

    return transactions


@router.post("/purchase", response_model=schemas.CoinPurchaseResponse)
def purchase_coins(
    request: schemas.CoinPurchaseRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Stripe Checkout Sessionを作成してコイン購入ページのURLを返す
    """
    # コインパックの存在確認
    if request.pack_id not in COIN_PACKS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="指定されたコインパックが存在しません"
        )

    pack = COIN_PACKS[request.pack_id]

    try:
        # Stripe Checkout Session作成
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": "jpy",
                    "product_data": {
                        "name": pack["name"],
                        "description": f"{pack['coins']}コインを購入",
                    },
                    "unit_amount": pack["price_jpy"],  # 円単位（JPYは最小単位が1円）
                },
                "quantity": 1,
            }],
            mode="payment",
            # 決済成功時のリダイレクトURL（session_idをクエリに含める）
            success_url=f"{FRONTEND_URL}/frontend/coins.html?success=true&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}/frontend/coins.html?canceled=true",
            metadata={
                "user_id": str(current_user.id),
                "pack_id": request.pack_id,
                "coins": str(pack["coins"]),
            }
        )
    except stripe.error.StripeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Stripe決済エラー: {str(e)}"
        )

    return schemas.CoinPurchaseResponse(
        checkout_url=session.url,
        session_id=session.id
    )


@router.post("/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """
    Stripe Webhookエンドポイント
    決済完了イベントを受け取り、コインをユーザーに付与する
    """
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    # Webhook署名を検証
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        # ペイロードが不正
        raise HTTPException(status_code=400, detail="無効なペイロードです")
    except stripe.error.SignatureVerificationError:
        # 署名が不正
        raise HTTPException(status_code=400, detail="Webhook署名の検証に失敗しました")

    # checkout.session.completed イベントを処理
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        # セッションのメタデータからユーザーIDとコイン数を取得
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        coins_to_add = metadata.get("coins")
        pack_id = metadata.get("pack_id")

        if not user_id or not coins_to_add:
            return {"status": "error", "message": "メタデータが不正です"}

        # 重複処理防止（同じStripeセッションIDで複数回コイン付与しない）
        existing_transaction = db.query(models.CoinTransaction).filter(
            models.CoinTransaction.stripe_session_id == session["id"]
        ).first()

        if existing_transaction:
            return {"status": "already_processed"}

        # ユーザー取得
        user = db.query(models.User).filter(
            models.User.id == int(user_id)
        ).first()

        if not user:
            return {"status": "error", "message": "ユーザーが見つかりません"}

        coins = int(coins_to_add)
        pack_info = COIN_PACKS.get(pack_id, {})

        # コインを付与
        user.coin_balance += coins

        # 取引履歴を記録
        transaction = models.CoinTransaction(
            user_id=user.id,
            amount=coins,
            transaction_type="purchase",
            stripe_session_id=session["id"],
            description=f"{pack_info.get('name', pack_id)}購入 ({pack_info.get('price_jpy', '?')}円)"
        )
        db.add(transaction)
        db.commit()

    return {"status": "success"}


@router.get("/packs")
def get_coin_packs():
    """
    購入可能なコインパック一覧を返す
    """
    packs = []
    for pack_id, pack_info in COIN_PACKS.items():
        packs.append({
            "id": pack_id,
            "name": pack_info["name"],
            "coins": pack_info["coins"],
            "price_jpy": pack_info["price_jpy"],
        })
    return packs
