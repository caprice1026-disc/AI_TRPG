from __future__ import annotations

import uuid
from typing import Dict, List, Optional

from sqlalchemy import select

from . import db, rules
from .models import Character, DiceLog, Session, TurnLog

db.init_db()


def _uid() -> str:
    # ランダムな ID を生成
    return uuid.uuid4().hex


def _character_to_dict(character: Character) -> Dict:
    # Character モデルを API 用の辞書に変換
    base_stats = db.loads(character.base_stats) or {}
    resources = db.loads(character.resources) or {}
    derived_stats = db.loads(character.derived_stats) or rules.compute_derived_stats(base_stats, resources)
    return {
        "id": character.id,
        "session_id": character.session_id,
        "name": character.name,
        "race": character.race,
        "clazz": character.clazz,
        "level": character.level,
        "base_stats": base_stats,
        "skills": db.loads(character.skills) or {},
        "resources": resources,
        "derived_stats": derived_stats,
        "created_at": character.created_at,
    }


def _session_to_dict(session: Session, include_children: bool = True) -> Dict:
    # Session モデルを API 用の辞書に変換
    payload = {
        "id": session.id,
        "name": session.name,
        "created_at": session.created_at,
        "settings": db.loads(session.settings) or {},
        "safety": db.loads(session.safety) or {},
        "save_blob": db.loads(session.save_blob) or {"messages": [], "world_facts": {}},
    }
    if include_children:
        payload["characters"] = [_character_to_dict(c) for c in session.characters]
        payload["turn_logs"] = list_turn_logs(session.id)
        payload["dice_logs"] = list_dice_logs(session.id)
    return payload


def create_session(name: Optional[str] = None, settings: Optional[Dict] = None, safety: Optional[Dict] = None) -> Dict:
    # セッションを新規作成
    session_id = _uid()
    with db.session_scope() as orm:
        model = Session(
            id=session_id,
            name=name or "session",
            settings=db.dumps(settings or {}),
            safety=db.dumps(safety or {}),
            save_blob=db.dumps({"messages": [], "world_facts": {}}),
        )
        orm.add(model)
    return get_session(session_id)


def get_session(session_id: str) -> Optional[Dict]:
    # セッション ID からデータを取得
    with db.session_scope() as orm:
        model = orm.get(Session, session_id)
        if not model:
            return None
        # 遅延評価のため明示的に children をロード
        _ = model.characters, model.turn_logs, model.dice_logs
        return _session_to_dict(model)


def list_turn_logs(session_id: str) -> List[Dict]:
    # ターンログ一覧を取得
    with db.session_scope() as orm:
        result = orm.execute(
            select(TurnLog).where(TurnLog.session_id == session_id).order_by(TurnLog.id.asc())
        )
        rows = []
        for row in result.scalars():
            rows.append(
                {
                    "id": row.id,
                    "session_id": row.session_id,
                    "turn_no": row.turn_no,
                    "player_input": row.player_input,
                    "gm_output": db.loads(row.gm_output) or {},
                    "dice_results": db.loads(row.dice_results) or [],
                    "world_diff": db.loads(row.world_diff) or {},
                    "created_at": row.created_at,
                }
            )
        return rows


def list_dice_logs(session_id: Optional[str] = None) -> List[Dict]:
    # ダイスログ一覧を取得（最新50件）
    with db.session_scope() as orm:
        stmt = select(DiceLog).order_by(DiceLog.id.desc()).limit(50)
        if session_id:
            stmt = stmt.where(DiceLog.session_id == session_id)
        result = orm.execute(stmt)
        rows = []
        for row in result.scalars():
            rows.append(
                {
                    "id": row.id,
                    "session_id": row.session_id,
                    "expression": row.expression,
                    "result": db.loads(row.result) or {},
                    "created_at": row.created_at,
                }
            )
        return rows


def list_characters(session_id: str) -> List[Dict]:
    # セッションに紐づくキャラクター一覧を取得
    with db.session_scope() as orm:
        result = orm.execute(select(Character).where(Character.session_id == session_id))
        return [_character_to_dict(c) for c in result.scalars()]


def create_character(
    session_id: str,
    name: str,
    race: str = "",
    clazz: str = "",
    level: int = 1,
    base_stats: Optional[Dict] = None,
    skills: Optional[Dict] = None,
    resources: Optional[Dict] = None,
) -> Dict:
    # キャラクターを新規作成
    base_stats = base_stats or {}
    resources = resources or {}
    derived_stats = rules.compute_derived_stats(base_stats, resources)
    char_id = _uid()
    with db.session_scope() as orm:
        model = Character(
            id=char_id,
            session_id=session_id,
            name=name,
            race=race,
            clazz=clazz,
            level=level,
            base_stats=db.dumps(base_stats),
            skills=db.dumps(skills or {}),
            resources=db.dumps(resources),
            derived_stats=db.dumps(derived_stats),
        )
        orm.add(model)
    return get_character(char_id)


def update_character(char_id: str, payload: Dict) -> Optional[Dict]:
    # キャラクター情報を更新
    with db.session_scope() as orm:
        model = orm.get(Character, char_id)
        if not model:
            return None
        current = _character_to_dict(model)
        base_stats = payload.get("base_stats", current.get("base_stats"))
        resources = payload.get("resources", current.get("resources"))
        derived_stats = rules.compute_derived_stats(base_stats, resources)
        model.name = payload.get("name", current["name"])
        model.race = payload.get("race", current.get("race"))
        model.clazz = payload.get("clazz", current.get("clazz"))
        model.level = payload.get("level", current.get("level"))
        model.base_stats = db.dumps(base_stats)
        model.skills = db.dumps(payload.get("skills", current.get("skills")) or {})
        model.resources = db.dumps(resources)
        model.derived_stats = db.dumps(derived_stats)
    return get_character(char_id)


def get_character(char_id: str) -> Optional[Dict]:
    # キャラクター ID からデータを取得
    with db.session_scope() as orm:
        model = orm.get(Character, char_id)
        if not model:
            return None
        return _character_to_dict(model)


def log_dice(session_id: Optional[str], expression: str, result: Dict) -> int:
    # ダイスロール結果をログ保存
    with db.session_scope() as orm:
        model = DiceLog(
            session_id=session_id,
            expression=expression,
            result=db.dumps(result),
        )
        orm.add(model)
        orm.flush()
        return model.id


def log_turn(
    session_id: str,
    turn_no: int,
    player_input: str,
    gm_output: Dict,
    dice_results: List[Dict],
    world_diff: Dict,
) -> int:
    # 1 ターン分の結果をログ保存
    with db.session_scope() as orm:
        model = TurnLog(
            session_id=session_id,
            turn_no=turn_no,
            player_input=player_input,
            gm_output=db.dumps(gm_output),
            dice_results=db.dumps(dice_results),
            world_diff=db.dumps(world_diff),
        )
        orm.add(model)
        orm.flush()
        return model.id


def update_session_save(session_id: str, save_blob: Dict) -> None:
    # セッションのセーブデータを更新
    with db.session_scope() as orm:
        model = orm.get(Session, session_id)
        if model:
            model.save_blob = db.dumps(save_blob)


def summarize_state(session: Dict) -> Dict:
    """Collapse session into a lightweight state payload for the front-end."""
    chars = []
    for c in session.get("characters", []):
        chars.append(
            {
                "id": c["id"],
                "name": c.get("name"),
                "hp": c.get("resources", {}).get("hp"),
                "max_hp": c.get("derived_stats", {}).get("max_hp"),
                "ac": c.get("derived_stats", {}).get("ac"),
                "conditions": c.get("resources", {}).get("conditions", []),
            }
        )
    return {
        "session_id": session["id"],
        "name": session.get("name"),
        "characters": chars,
        "world_facts": session.get("save_blob", {}).get("world_facts", {}),
    }


def apply_hp_update(char_id: str, new_hp: int) -> Optional[Dict]:
    # HP の更新を適用
    char = get_character(char_id)
    if not char:
        return None
    resources = dict(char.get("resources", {}))
    resources["hp"] = max(0, new_hp)
    return update_character(char_id, {"resources": resources})
