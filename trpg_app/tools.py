from __future__ import annotations

import random
from typing import Dict, Optional

from . import rules
from . import services


class Toolset:
    """Server-side tools exposed to the GM agent."""

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.rng = random.Random()

    def request_skill_check(self, actor_id: str, skill: str, dc: int) -> Dict:
        # 技能判定ツール（AI GM 用）
        actor = services.get_character(actor_id)
        if not actor:
            return {"error": f"character {actor_id} not found"}
        outcome = rules.request_skill_check(actor, skill, dc, rng=self.rng)
        services.log_dice(self.session_id, f"skill:{skill}", {"rolls": outcome.rolls, "total": outcome.total})
        return {
            "type": "skill_check",
            "actor_id": actor_id,
            "skill": skill,
            "dc": dc,
            "success": outcome.success,
            "detail": outcome.detail,
            "total": outcome.total,
            "rolls": outcome.rolls,
        }

    def attack_roll(self, attacker_id: str, target_id: str, weapon: Optional[Dict] = None) -> Dict:
        # 攻撃判定ツール（AI GM 用）
        attacker = services.get_character(attacker_id)
        target = services.get_character(target_id)
        if not attacker or not target:
            return {"error": "attacker or target missing"}
        outcome = rules.attack_roll(attacker, target, weapon=weapon, rng=self.rng)
        services.log_dice(self.session_id, f"attack:{weapon}", {"rolls": outcome.rolls, "total": outcome.total})
        if "target_hp" in outcome.updates:
            updated = services.apply_hp_update(target_id, outcome.updates["target_hp"])
        else:
            updated = target
        return {
            "type": "attack",
            "attacker_id": attacker_id,
            "target_id": target_id,
            "success": outcome.success,
            "detail": outcome.detail,
            "rolls": outcome.rolls,
            "target": updated,
        }

    def query_game_state(self, selector: Optional[str] = None) -> Dict:
        # 状態参照ツール
        session = services.get_session(self.session_id)
        if not session:
            return {"error": "session not found"}
        state = services.summarize_state(session)
        if selector == "characters":
            return {"characters": state["characters"]}
        return state

    def update_world_fact(self, key: str, value) -> Dict:
        # 世界フラグ更新ツール
        session = services.get_session(self.session_id)
        if not session:
            return {"error": "session not found"}
        save_blob = dict(session.get("save_blob") or {})
        world_facts = dict(save_blob.get("world_facts") or {})
        world_facts[key] = value
        save_blob["world_facts"] = world_facts
        services.update_session_save(self.session_id, save_blob)
        return {"world_facts": world_facts, "updated": {key: value}}

    def evaluate_rule(self, actor_id: str, template: Dict, target_id: Optional[str] = None) -> Dict:
        # ルールテンプレートを評価する汎用ツール
        actor = services.get_character(actor_id)
        target = services.get_character(target_id) if target_id else None
        if not actor:
            return {"error": "actor not found"}
        outcome = rules.evaluate_rule_template(template, actor, target, rng=self.rng)
        services.log_dice(
            self.session_id,
            f"rule:{template.get('type')}",
            {"rolls": outcome.rolls, "total": outcome.total, "detail": outcome.detail},
        )
        if "target_hp" in outcome.updates and target_id:
            target = services.apply_hp_update(target_id, outcome.updates["target_hp"])
        return {
            "type": template.get("type"),
            "actor_id": actor_id,
            "target_id": target_id,
            "success": outcome.success,
            "detail": outcome.detail,
            "rolls": outcome.rolls,
            "updates": outcome.updates,
            "target": target,
        }
