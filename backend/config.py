"""
アプリケーション設定ファイル
環境変数から設定値を読み込む
"""
import os
from dotenv import load_dotenv

# .envファイルがあれば読み込む
load_dotenv()

# JWT認証用の秘密鍵（本番環境では必ず環境変数で上書きすること）
SECRET_KEY = os.getenv("SECRET_KEY", "oripa-gacha-secret-key-change-in-production")

# JWTアルゴリズム
ALGORITHM = "HS256"

# JWTトークンの有効期限（分）
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24時間

# Stripeの秘密鍵（バックエンドのみで使用 - 絶対に外部に公開しないこと）
STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "sk_test_your_stripe_secret_key_here")

# Stripeの公開鍵（フロントエンドに返却しても安全なキー）
STRIPE_PUBLIC_KEY = os.getenv("STRIPE_PUBLIC_KEY", "pk_test_your_key_here")

# StripeのWebhook署名シークレット（Webhook検証用 - 秘密にすること）
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "whsec_your_webhook_secret_here")

# フロントエンドのURL（Stripe成功・キャンセルリダイレクト先）
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")

# データベースURL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./oripa_gacha.db")

# 管理者メールアドレス（このメールで登録したユーザーが自動的にis_admin=Trueになる）
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "")

# コインパック定義（コイン数: 価格(円)）
# 100コイン = 100円 に統一
COIN_PACKS = {
    "pack_100": {"coins": 100, "price_jpy": 100, "name": "100コイン"},
    "pack_500": {"coins": 500, "price_jpy": 500, "name": "500コイン"},
    "pack_1000": {"coins": 1000, "price_jpy": 1000, "name": "1000コイン"},
}
