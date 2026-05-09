"""
データベース接続設定
SQLAlchemyを使ってSQLiteまたはPostgreSQLに接続する
DATABASE_URL環境変数でDBを切り替え可能（Render/本番はPostgresSQL推奨）
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import DATABASE_URL

# SQLite の場合のみ check_same_thread=False が必要
# PostgreSQL等の場合はconnect_argsを渡さない
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
else:
    # PostgreSQL / MySQL など（Renderの本番環境）
    # postgres:// は SQLAlchemy 1.4+ では postgresql:// が必要
    _url = DATABASE_URL
    if _url.startswith("postgres://"):
        _url = _url.replace("postgres://", "postgresql://", 1)
    engine = create_engine(_url)

# セッションファクトリ作成
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# モデルの基底クラス
Base = declarative_base()


def get_db():
    """
    データベースセッションの依存性注入用ジェネレーター
    FastAPIのDependsで使用する
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
