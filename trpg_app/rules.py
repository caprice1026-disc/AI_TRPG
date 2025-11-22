from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from . import dice

SKILL_TO_ABILITY = {
    "perception": "WIS",
    "stealth": "DEX",
    "athletics": "STR",
    "acrobatics": "DEX",
    "investigation": "INT",
    "survival": "WIS",
    "persuasion": "CHA",
}


def ability_mod(score: int) -> int:
    # 能力値から修正値を算出
    return (score - 10) // 2


def compute_derived_stats(base_stats: Dict[str, int], resources: Dict) -> Dict:
    # 派生ステータス（AC/HPなど）を計算
    mods = {k: ability_mod(int(v)) for k, v in (base_stats or {}).items()}
    dex_mod = mods.get("DEX", 0)
    armor_bonus = int(resources.get("ac_bonus", 0)) if resources else 0
    base_ac = 10 + dex_mod + armor_bonus
    hp = resources.get("hp", 0) if resources else 0
    max_hp = resources.get("max_hp", hp) if resources else hp
    return {
        "mods": mods,
        "ac": base_ac,
        "hp": hp,
        "max_hp": max_hp,
    }


@dataclass
class RuleOutcome:
    success: bool
    total: int
    dc: int
    detail: str
    rolls: list
    updates: Dict


def request_skill_check(actor: Dict, skill: str, dc: int, rng=None) -> RuleOutcome:
    # 技能判定を実行
    base_stats = actor.get("base_stats", {})
    skills = actor.get("skills", {}) or {}
    ability_key = SKILL_TO_ABILITY.get(skill.lower(), "DEX")
    mod = ability_mod(int(base_stats.get(ability_key, 10)))
    skill_bonus = int(skills.get(skill, skills.get(skill.lower(), 0)) or 0)
    roll_result = dice.roll("1d20", rng=rng)
    total = roll_result["total"] + mod + skill_bonus
    breakdown = (
        f"1d20({roll_result['total']}) + mod({mod}) + skill({skill_bonus}) = {total}"
    )
    success = total >= dc
    detail = f"{skill} check vs DC {dc}: {'success' if success else 'failure'} ({breakdown})"
    return RuleOutcome(
        success=success,
        total=total,
        dc=dc,
        detail=detail,
        rolls=roll_result["rolls"],
        updates={},
    )


def attack_roll(
    attacker: Dict,
    target: Dict,
    dc_ac: Optional[int] = None,
    weapon: Optional[Dict] = None,
    rng=None,
) -> RuleOutcome:
    # 攻撃ロールとダメージ適用を実行
    weapon = weapon or attacker.get("weapon") or {}
    attack_bonus = int(weapon.get("attack_bonus", 0))
    base_stats = attacker.get("base_stats", {})
    prof = int(attacker.get("resources", {}).get("proficiency", 2))
    str_mod = ability_mod(int(base_stats.get("STR", 10)))
    dex_mod = ability_mod(int(base_stats.get("DEX", 10)))
    ability_bonus = dex_mod if weapon.get("finesse") else str_mod
    attack_bonus = attack_bonus + ability_bonus + prof
    ac = dc_ac or target.get("derived_stats", {}).get("ac", 10)

    attack_roll_result = dice.roll("1d20", rng=rng)
    attack_total = attack_roll_result["total"] + attack_bonus
    hit = attack_total >= ac

    damage_expr = weapon.get("damage", "1d6")
    damage_roll = dice.roll(damage_expr, rng=rng)
    damage_bonus = int(weapon.get("damage_bonus", ability_bonus))
    damage_total = damage_roll["total"] + damage_bonus
    dealt = damage_total if hit else 0

    target_hp = int(target.get("resources", {}).get("hp", 0))
    remaining_hp = max(0, target_hp - dealt) if hit else target_hp

    detail = (
        f"Attack vs AC {ac}: roll {attack_roll_result['total']} + bonus {attack_bonus}"
        f" = {attack_total} -> {'HIT' if hit else 'MISS'}; "
        f"damage {damage_expr} ({damage_roll['total']}) + {damage_bonus} = {damage_total} "
        f"applied: {dealt}, target hp {target_hp}->{remaining_hp}"
    )
    updates = {"target_hp": remaining_hp} if hit else {}
    all_rolls = attack_roll_result["rolls"] + damage_roll["rolls"]
    return RuleOutcome(
        success=hit,
        total=attack_total,
        dc=ac,
        detail=detail,
        rolls=all_rolls,
        updates=updates,
    )


def saving_throw(actor: Dict, dc: int, save_type: str, rng=None) -> RuleOutcome:
    # セービングスローを実行
    base_stats = actor.get("base_stats", {})
    mod = ability_mod(int(base_stats.get(save_type.upper(), 10)))
    roll_result = dice.roll("1d20", rng=rng)
    total = roll_result["total"] + mod
    success = total >= dc
    detail = (
        f"{save_type} save vs DC {dc}: 1d20({roll_result['total']}) + mod({mod}) = {total} "
        f"{'success' if success else 'failure'}"
    )
    return RuleOutcome(
        success=success,
        total=total,
        dc=dc,
        detail=detail,
        rolls=roll_result["rolls"],
        updates={},
    )


def evaluate_rule_template(template: Dict, actor: Dict, target: Optional[Dict] = None, rng=None) -> RuleOutcome:
    """簡易 JSON ルールテンプレートを解釈し、対応する判定を実行する。"""
    rtype = (template.get("type") or "").lower()
    if rtype in ("skill", "skill_check"):
        return request_skill_check(actor, template.get("skill", "perception"), int(template.get("dc", 10)), rng=rng)
    if rtype == "attack":
        weapon = template.get("weapon") or {}
        dc_ac = template.get("dc") or (target or {}).get("derived_stats", {}).get("ac")
        return attack_roll(actor, target or {}, dc_ac=dc_ac, weapon=weapon, rng=rng)
    if rtype in ("save", "saving_throw"):
        save_type = template.get("save_type", "DEX")
        return saving_throw(actor, int(template.get("dc", 10)), save_type, rng=rng)
    raise ValueError(f"Unknown rule template type: {rtype}")
