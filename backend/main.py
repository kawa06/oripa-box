"""
FastAPIアプリケーション エントリポイント
全ルーターを登録し、アプリを起動する
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.database import engine, Base, SessionLocal
from backend.routes import auth, gacha, coins, packs, admin, collection, exchange, ranking
from backend import config, models

# テーブルが存在しない場合は自動作成
Base.metadata.create_all(bind=engine)

# ===== 起動時マイグレーション =====
# 既存テーブルに不足カラムを追加する（ALTER TABLE）
# カラムが既に存在する場合はエラーを無視する
_MISSING_COLUMNS = [
    # (テーブル名, カラム名, カラム定義SQL)
    ("users", "is_verified",  "BOOLEAN DEFAULT 1 NOT NULL"),
    ("users", "is_admin",     "BOOLEAN DEFAULT 0 NOT NULL"),
    ("users", "is_active",    "BOOLEAN DEFAULT 1 NOT NULL"),
    ("users", "points",       "INTEGER DEFAULT 0 NOT NULL"),
    ("packs", "probabilities","TEXT"),
    ("packs", "image_url",    "TEXT"),
    ("cards", "image_url",    "TEXT"),
]

_raw_conn = engine.raw_connection()
try:
    _cur = _raw_conn.cursor()
    for table, col, coldef in _MISSING_COLUMNS:
        try:
            _cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")
            print(f"[マイグレーション] {table}.{col} を追加しました")
        except Exception:
            # カラムが既に存在する場合は無視
            pass
    _raw_conn.commit()
except Exception as e:
    print(f"[マイグレーション] エラー: {e}")
finally:
    _raw_conn.close()

# SMTP未設定の環境では、既存ユーザーの is_verified を全件 True に更新する
# （SMTPが設定されていない状態で登録したユーザーがログインできない問題を修正）
if not config.SMTP_ENABLED:
    _db = SessionLocal()
    try:
        updated_count = (
            _db.query(models.User)
            .filter(models.User.is_verified == False)
            .update({"is_verified": True}, synchronize_session=False)
        )
        _db.commit()
        if updated_count > 0:
            print(f"[起動時マイグレーション] SMTP未設定のため {updated_count} 件のユーザーの is_verified を True に更新しました")
    except Exception as e:
        print(f"[起動時マイグレーション] エラー: {e}")
        _db.rollback()
    finally:
        _db.close()

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
app.include_router(admin.router)
app.include_router(collection.router)
app.include_router(exchange.router)
app.include_router(ranking.router)

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


# 新規フロントエンドページへのルーティング
@app.get("/admin")
def admin_page():
    """管理画面"""
    return FileResponse(os.path.join(frontend_path, "admin.html"))


@app.get("/collection")
def collection_page():
    """コレクション画面"""
    return FileResponse(os.path.join(frontend_path, "collection.html"))


@app.get("/history")
def history_page():
    """ガチャ履歴画面"""
    return FileResponse(os.path.join(frontend_path, "history.html"))


@app.get("/exchange")
def exchange_page():
    """ポイント交換画面"""
    return FileResponse(os.path.join(frontend_path, "exchange.html"))


@app.get("/ranking")
def ranking_page():
    """ランキング画面"""
    return FileResponse(os.path.join(frontend_path, "ranking.html"))


@app.get("/terms")
def terms_page():
    """利用規約画面"""
    return FileResponse(os.path.join(frontend_path, "terms.html"))


@app.get("/legal")
def legal_page():
    """特定商取引法に基づく表記"""
    return FileResponse(os.path.join(frontend_path, "legal.html"))


@app.get("/verify-email")
def verify_email_page():
    """メールアドレス認証ページ（メール内リンクからのアクセス用）"""
    return FileResponse(os.path.join(frontend_path, "verify-email.html"))


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


if __name__ == "__main__":
    import uvicorn
    # Render.com は PORT 環境変数でポートを指定する
    # ローカル開発時はデフォルトで 8000 番を使用
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
