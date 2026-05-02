"""
データベース接続設定
SQLAlchemyを使ってSQLiteに接続する
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.config import DATABASE_URL

# SQLiteエンジン作成
# check_same_thread=False はSQLite特有の設定（FastAPIの非同期処理対応）
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

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
