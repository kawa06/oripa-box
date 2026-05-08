"""
SQLAlchemy データベースモデル定義
ユーザー、パック、カード、在庫、コイントランザクションを管理する
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean,
    DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from backend.database import Base


class User(Base):
    """ユーザーモデル"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)  # メールアドレス
    username = Column(String, unique=True, index=True, nullable=False)  # ユーザー名
    hashed_password = Column(String, nullable=False)  # ハッシュ化パスワード
    coin_balance = Column(Integer, default=0, nullable=False)  # コイン残高
    is_active = Column(Boolean, default=True)  # アカウント有効フラグ
    is_admin = Column(Boolean, default=False)  # 管理者フラグ
    is_verified = Column(Boolean, default=False)  # メール認証済みフラグ
    points = Column(Integer, default=0, nullable=False)  # 交換ポイント残高
    created_at = Column(DateTime, default=datetime.utcnow)  # 作成日時

    # リレーション
    coin_transactions = relationship("CoinTransaction", back_populates="user")
    gacha_results = relationship("GachaResult", back_populates="user")
    pity_counters = relationship("PityCounter", back_populates="user")
    user_cards = relationship("UserCard", back_populates="user")
    shipping_addresses = relationship("ShippingAddress", back_populates="user")
    shipping_requests = relationship("ShippingRequest", back_populates="user")


class Pack(Base):
    """ガチャパックモデル"""
    __tablename__ = "packs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)  # パック名
    description = Column(Text)  # パック説明
    price_coins = Column(Integer, nullable=False)  # ガチャに必要なコイン数
    stock = Column(Integer, default=100, nullable=False)  # 在庫数（最大100口）
    max_stock = Column(Integer, default=100, nullable=False)  # 最大在庫数
    image_url = Column(String)  # パック画像URL
    is_active = Column(Boolean, default=True)  # 販売中フラグ
    # 各賞の排出確率設定（JSON文字列: {"A賞":5,"B賞":10,"C賞":20,"D賞":30,"E賞":35} のように整数%で指定）
    # Noneの場合はデフォルト確率（A賞1,B賞4,C賞15,D賞30,E賞50）を使用
    probabilities = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # リレーション
    cards = relationship("Card", back_populates="pack")
    gacha_results = relationship("GachaResult", back_populates="pack")
    pity_counters = relationship("PityCounter", back_populates="pack")


class Card(Base):
    """カードモデル（ガチャで排出されるカード）"""
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    pack_id = Column(Integer, ForeignKey("packs.id"), nullable=False)  # 所属パック
    name = Column(String, nullable=False)  # カード名
    rarity = Column(String, nullable=False)  # 賞（A賞/B賞/C賞/D賞/E賞）
    probability = Column(Float, nullable=False)  # 排出確率（0.0〜1.0）
    image_url = Column(String)  # カード画像URL
    description = Column(Text)  # カード説明
    # コイン変換時の獲得コイン数（Noneの場合は賞ごとのデフォルト値を使用）
    coin_value = Column(Integer, nullable=True)

    # リレーション
    pack = relationship("Pack", back_populates="cards")
    user_cards = relationship("UserCard", back_populates="card")


class GachaResult(Base):
    """ガチャ結果履歴モデル"""
    __tablename__ = "gacha_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 実行ユーザー
    pack_id = Column(Integer, ForeignKey("packs.id"), nullable=False)  # 実行パック
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)  # 排出カード
    coins_spent = Column(Integer, nullable=False)  # 消費コイン数
    created_at = Column(DateTime, default=datetime.utcnow)  # 実行日時

    # リレーション
    user = relationship("User", back_populates="gacha_results")
    pack = relationship("Pack", back_populates="gacha_results")
    card = relationship("Card")


class CoinTransaction(Base):
    """コイン取引履歴モデル"""
    __tablename__ = "coin_transactions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ユーザー
    amount = Column(Integer, nullable=False)  # コイン増減量（+で増加、-で減少）
    transaction_type = Column(String, nullable=False)  # 取引種別（purchase/gacha/bonus）
    stripe_session_id = Column(String)  # Stripe セッションID（購入時のみ）
    description = Column(String)  # 取引説明
    created_at = Column(DateTime, default=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="coin_transactions")


class PityCounter(Base):
    """天井（ピティ）カウンターモデル
    ユーザーがパックごとに何回ガチャを引いたかを記録する
    50回でA賞確定
    """
    __tablename__ = "pity_counters"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ユーザー
    pack_id = Column(Integer, ForeignKey("packs.id"), nullable=False)  # パック
    count = Column(Integer, default=0, nullable=False)  # 天井カウント（A賞排出でリセット）
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="pity_counters")
    pack = relationship("Pack", back_populates="pity_counters")


class UserCard(Base):
    """ユーザー所持カードモデル（コレクション）"""
    __tablename__ = "user_cards"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ユーザー
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)  # カード
    count = Column(Integer, default=1, nullable=False)  # 所持枚数
    # カードのステータス: owned=所持中, shipping_requested=発送申請中, shipped=発送済み
    status = Column(String, default="owned", nullable=False)
    obtained_at = Column(DateTime, default=datetime.utcnow)  # 最初に入手した日時

    # リレーション
    user = relationship("User", back_populates="user_cards")
    card = relationship("Card", back_populates="user_cards")
    shipping_requests = relationship("ShippingRequest", back_populates="user_card")


class ShippingAddress(Base):
    """ユーザーの発送先住所モデル"""
    __tablename__ = "shipping_addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # ユーザー
    name = Column(String, nullable=False)           # 氏名
    postal_code = Column(String, nullable=False)    # 郵便番号
    prefecture = Column(String, nullable=False)     # 都道府県
    city = Column(String, nullable=False)           # 市区町村
    address = Column(String, nullable=False)        # 番地
    building = Column(String, nullable=True)        # 建物名（任意）
    phone = Column(String, nullable=False)          # 電話番号
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="shipping_addresses")
    shipping_requests = relationship("ShippingRequest", back_populates="address")


class ShippingRequest(Base):
    """発送申請モデル"""
    __tablename__ = "shipping_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)          # ユーザー
    user_card_id = Column(Integer, ForeignKey("user_cards.id"), nullable=False) # 発送するカード
    address_id = Column(Integer, ForeignKey("shipping_addresses.id"), nullable=False)  # 発送先住所
    # ステータス: pending=発送待ち, shipped=発送済み, completed=完了
    status = Column(String, default="pending", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # リレーション
    user = relationship("User", back_populates="shipping_requests")
    user_card = relationship("UserCard", back_populates="shipping_requests")
    address = relationship("ShippingAddress", back_populates="shipping_requests")
