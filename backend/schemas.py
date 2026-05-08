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
    is_admin: bool = False
    points: int = 0
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
    pity_count: int = 0          # 現在の天井カウント（UR排出後はリセット済み）
    pity_triggered: bool = False  # 天井が発動したかどうか


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


# ===== コレクション関連スキーマ =====

class UserCardResponse(BaseModel):
    """ユーザー所持カードレスポンス"""
    id: int
    card_id: int
    card_name: str
    card_rarity: str
    card_image_url: Optional[str] = None
    card_description: Optional[str] = None
    pack_name: str
    count: int
    obtained_at: datetime

    class Config:
        from_attributes = True


# ===== 交換関連スキーマ =====

class ExchangeRequest(BaseModel):
    """カード交換リクエスト"""
    user_card_id: int   # 交換するユーザー所持カードID（ポイントに変換）


class ExchangeCardRequest(BaseModel):
    """ポイントでカード入手リクエスト"""
    card_id: int        # 入手するカードのID


class PointBalanceResponse(BaseModel):
    """ポイント残高レスポンス"""
    points: int


# ===== 管理者関連スキーマ =====

class AdminUserResponse(BaseModel):
    """管理者向けユーザー情報レスポンス"""
    id: int
    email: str
    username: str
    coin_balance: int
    points: int
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class AdminGrantCoinsRequest(BaseModel):
    """コイン付与リクエスト"""
    user_id: int
    amount: int
    description: Optional[str] = "管理者によるコイン付与"


class AdminPackCreate(BaseModel):
    """パック作成リクエスト"""
    name: str
    description: Optional[str] = None
    price_coins: int
    stock: int = 100
    max_stock: int = 100
    image_url: Optional[str] = None
    is_active: bool = True


class AdminPackUpdate(BaseModel):
    """パック更新リクエスト"""
    name: Optional[str] = None
    description: Optional[str] = None
    price_coins: Optional[int] = None
    stock: Optional[int] = None
    max_stock: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None


class AdminCardCreate(BaseModel):
    """カード作成リクエスト"""
    pack_id: int
    name: str
    rarity: str
    probability: float
    image_url: Optional[str] = None
    description: Optional[str] = None


class AdminCardUpdate(BaseModel):
    """カード更新リクエスト"""
    name: Optional[str] = None
    rarity: Optional[str] = None
    probability: Optional[float] = None
    image_url: Optional[str] = None
    description: Optional[str] = None


# ===== ランキング関連スキーマ =====

class RankingEntry(BaseModel):
    """ランキングエントリー"""
    rank: int
    username: str
    ur_count: int
