import json
import os
from contextlib import contextmanager
from typing import Any, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

DB_PATH = os.getenv("TRPG_DB_PATH", "trpg.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLAlchemy エンジンとセッションファクトリを初期化
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    # テーブルを作成（存在しない場合のみ）
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Session:
    # トランザクション境界を提供するユーティリティ
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def dumps(data: Any) -> str:
    # JSON 文字列へ変換（日本語もそのまま保持）
    return json.dumps(data, ensure_ascii=False)


def loads(raw: Optional[str]) -> Any:
    # JSON 文字列を辞書へ戻す
    return json.loads(raw) if raw else None
