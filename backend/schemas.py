"""
Pydanticスキーマ定義
APIのリクエスト・レスポンスの型を定義する
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


# ===== ユーザー関連スキーマ =====

class UserCreate(BaseModel):
    """ユーザー登録リクエスト"""
    email: EmailStr
    username: str
    password: str


class UserLogin(BaseModel):
    """ログインリクエスト"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """ユーザー情報レスポンス"""
    id: int
    email: str
    username: str
    coin_balance: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """JWTトークンレスポンス"""
    access_token: str
    token_type: str
    user: UserResponse


# ===== カード関連スキーマ =====

class CardResponse(BaseModel):
    """カード情報レスポンス"""
    id: int
    name: str
    rarity: str
    probability: float
    image_url: Optional[str] = None
    description: Optional[str] = None

    class Config:
        from_attributes = True


# ===== パック関連スキーマ =====

class PackResponse(BaseModel):
    """パック情報レスポンス"""
    id: int
    name: str
    description: Optional[str] = None
    price_coins: int
    stock: int
    max_stock: int
    image_url: Optional[str] = None
    is_active: bool
    cards: List[CardResponse] = []

    class Config:
        from_attributes = True


class PackListResponse(BaseModel):
    """パック一覧レスポンス"""
    id: int
    name: str
    description: Optional[str] = None
    price_coins: int
    stock: int
    max_stock: int
    image_url: Optional[str] = None
    is_active: bool

    class Config:
        from_attributes = True


# ===== ガチャ関連スキーマ =====

class GachaRequest(BaseModel):
    """ガチャ実行リクエスト"""
    pack_id: int


class GachaResultResponse(BaseModel):
    """ガチャ結果レスポンス"""
    card: CardResponse
    coins_spent: int
    remaining_balance: int
    pack_remaining_stock: int


# ===== コイン関連スキーマ =====

class CoinBalanceResponse(BaseModel):
    """コイン残高レスポンス"""
    balance: int


class CoinPurchaseRequest(BaseModel):
    """コイン購入リクエスト"""
    pack_id: str  # "pack_100", "pack_500", "pack_1000"


class CoinPurchaseResponse(BaseModel):
    """コイン購入レスポンス（Stripe Checkout URL）"""
    checkout_url: str
    session_id: str


class CoinTransactionResponse(BaseModel):
    """コイン取引履歴レスポンス"""
    id: int
    amount: int
    transaction_type: str
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
