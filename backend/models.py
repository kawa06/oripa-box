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
    obtained_at = Column(DateTime, default=datetime.utcnow)  # 最初に入手した日時

    # リレーション
    user = relationship("User", back_populates="user_cards")
    card = relationship("Card", back_populates="user_cards")
