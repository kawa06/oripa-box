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
    is_verified: bool = False  # メール認証済みフラグ
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
    # コイン変換レート（Noneの場合はフロントエンドがデフォルト値を使用）
    coin_value: Optional[int] = None

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
    probabilities: Optional[str] = None  # 各賞確率JSON文字列
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
    probabilities: Optional[str] = None  # 各賞確率JSON文字列

    class Config:
        from_attributes = True


# ===== ガチャ関連スキーマ =====

class GachaRequest(BaseModel):
    """ガチャ実行リクエスト（1回 / 10回 / 100回）"""
    pack_id: int
    count: int = 1  # 引く枚数（1, 10, 100）


class GachaResultResponse(BaseModel):
    """ガチャ結果レスポンス（1回引き）"""
    card: CardResponse
    user_card_id: Optional[int] = None  # UserCard.id（コイン変換・発送申請に必要）
    coins_spent: int
    remaining_balance: int
    pack_remaining_stock: int
    pity_count: int = 0          # 現在の天井カウント（A賞排出後はリセット済み）
    pity_triggered: bool = False  # 天井が発動したかどうか


class MultiGachaResultResponse(BaseModel):
    """まとめ引きガチャ結果レスポンス（10回・100回）"""
    cards: List[GachaResultResponse]   # 各回の結果リスト
    total_coins_spent: int             # 消費コイン合計
    remaining_balance: int             # 引き後のコイン残高
    pack_remaining_stock: int          # 引き後の在庫
    pity_count: int = 0                # 最終天井カウント
    count: int = 1                     # 実際に引いた枚数
    # サマリー情報（100回引き用）
    rarity_summary: dict = {}          # 賞ごとの枚数 {"A賞": 1, "B賞": 3, ...}


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
    is_verified: bool = False  # メール認証済みフラグ
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
    # 各賞の確率設定（JSON文字列: {"A賞":5,"B賞":10,"C賞":20,"D賞":30,"E賞":35}）
    # 合計が100でない場合は警告を返す（バリデーションはフロントエンド側でも実施）
    probabilities: Optional[str] = None


class AdminPackUpdate(BaseModel):
    """パック更新リクエスト"""
    name: Optional[str] = None
    description: Optional[str] = None
    price_coins: Optional[int] = None
    stock: Optional[int] = None
    max_stock: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None
    # 各賞の確率設定（JSON文字列）
    probabilities: Optional[str] = None


class AdminCardCreate(BaseModel):
    """カード作成リクエスト"""
    pack_id: int
    name: str
    rarity: str
    probability: float
    image_url: Optional[str] = None
    description: Optional[str] = None
    # コイン変換レート（Noneの場合は賞別デフォルト値を使用）
    coin_value: Optional[int] = None


class AdminCardUpdate(BaseModel):
    """カード更新リクエスト"""
    name: Optional[str] = None
    rarity: Optional[str] = None
    probability: Optional[float] = None
    image_url: Optional[str] = None
    description: Optional[str] = None
    # コイン変換レート（Noneの場合は賞別デフォルト値を使用）
    coin_value: Optional[int] = None


# ===== ランキング関連スキーマ =====

class RankingEntry(BaseModel):
    """ランキングエントリー"""
    rank: int
    username: str
    ur_count: int  # A賞獲得数（フィールド名は後方互換のためur_countのまま）


# ===== 発送・住所関連スキーマ =====

class ShippingAddressCreate(BaseModel):
    """住所作成・更新リクエスト"""
    name: str
    postal_code: str
    prefecture: str
    city: str
    address: str
    building: Optional[str] = None
    phone: str


class ShippingAddressResponse(BaseModel):
    """住所レスポンス"""
    id: int
    name: str
    postal_code: str
    prefecture: str
    city: str
    address: str
    building: Optional[str] = None
    phone: str

    class Config:
        from_attributes = True


class ShippingRequestCreate(BaseModel):
    """発送申請リクエスト"""
    user_card_id: int    # 発送するカードのユーザーカードID
    address_id: int      # 発送先住所ID
    count: int = 1       # 発送する枚数（デフォルト1）


class ShippingRequestResponse(BaseModel):
    """発送申請レスポンス（管理者向け詳細）"""
    id: int
    status: str
    created_at: datetime
    updated_at: datetime
    # ユーザー情報
    username: str
    user_email: str
    # カード情報
    card_name: str
    card_rarity: str
    pack_name: str
    # 住所情報
    address_name: str
    postal_code: str
    prefecture: str
    city: str
    address: str
    building: Optional[str] = None
    phone: str

    class Config:
        from_attributes = True


class ConvertToCoinsRequest(BaseModel):
    """カードをコインに変換するリクエスト"""
    user_card_id: int    # 変換するカードのユーザーカードID
    count: int = 1       # 変換する枚数（デフォルト1）


class ShippingStatusUpdate(BaseModel):
    """発送ステータス更新リクエスト（管理者用）"""
    status: str  # pending/shipped/completed


# ===== 一括操作関連スキーマ =====

class BulkConvertRequest(BaseModel):
    """複数カードを一括コイン変換するリクエスト"""
    card_ids: List[int]                  # 変換するユーザーカードIDの配列
    counts: Optional[List[int]] = None   # 各カードの変換枚数（未指定時は全枚数変換）


class BulkShipRequest(BaseModel):
    """複数カードを一括発送申請するリクエスト"""
    card_ids: List[int]   # 発送申請するユーザーカードIDの配列
    address_id: int       # 発送先住所ID
