from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Session(Base):
    # セッションの永続データを表すテーブル
    __tablename__ = "sessions"

    id = Column(String, primary_key=True)
    name = Column(String)
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z")
    settings = Column(Text)
    safety = Column(Text)
    save_blob = Column(Text)

    characters = relationship("Character", back_populates="session", cascade="all, delete-orphan")
    turn_logs = relationship("TurnLog", back_populates="session", cascade="all, delete-orphan")
    dice_logs = relationship("DiceLog", back_populates="session", cascade="all, delete-orphan")


class Character(Base):
    # キャラクター情報を保持するテーブル
    __tablename__ = "characters"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    name = Column(String, nullable=False)
    race = Column(String)
    clazz = Column(String)
    level = Column(Integer)
    base_stats = Column(Text)
    skills = Column(Text)
    resources = Column(Text)
    derived_stats = Column(Text)
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z")

    session = relationship("Session", back_populates="characters")


class TurnLog(Base):
    # 各ターンの結果ログを保持するテーブル
    __tablename__ = "turn_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    turn_no = Column(Integer)
    player_input = Column(Text)
    gm_output = Column(Text)
    dice_results = Column(Text)
    world_diff = Column(Text)
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z")

    session = relationship("Session", back_populates="turn_logs")


class DiceLog(Base):
    # ダイスロールの履歴を保持するテーブル
    __tablename__ = "dice_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("sessions.id"))
    expression = Column(Text)
    result = Column(Text)
    created_at = Column(String, nullable=False, default=lambda: datetime.utcnow().isoformat() + "Z")

    session = relationship("Session", back_populates="dice_logs")
