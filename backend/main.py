"""
FastAPIアプリケーション エントリポイント
全ルーターを登録し、アプリを起動する
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.database import engine, Base
from backend.routes import auth, gacha, coins, packs
from backend import config

# テーブルが存在しない場合は自動作成
Base.metadata.create_all(bind=engine)

# FastAPIアプリケーション作成
app = FastAPI(
    title="オリパガチャ API",
    description="トレーディングカードのオリパガチャサービスAPI",
    version="1.0.0"
)

# CORSミドルウェア設定（開発環境では全オリジンを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では特定のオリジンに絞ること
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーターを登録
app.include_router(auth.router)
app.include_router(packs.router)
app.include_router(gacha.router)
app.include_router(coins.router)

# フロントエンドの静的ファイルを配信
frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")
if os.path.exists(frontend_path):
    app.mount("/frontend", StaticFiles(directory=frontend_path, html=True), name="frontend")


@app.get("/")
def root():
    """
    ルートにアクセスするとフロントエンドのトップページにリダイレクト
    """
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.get("/health")
def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok", "message": "オリパガチャAPIは正常に動作中です"}


@app.get("/api/config")
def get_config():
    """
    フロントエンド向け設定エンドポイント
    Stripeの公開鍵など、クライアントに渡しても安全な設定値のみを返す
    秘密鍵・Webhookシークレット等は絶対に返さない
    """
    return {
        "stripe_public_key": config.STRIPE_PUBLIC_KEY,
    }
