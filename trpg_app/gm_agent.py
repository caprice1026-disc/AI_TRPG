from __future__ import annotations

import os
from typing import Dict, List, Optional

from . import services
from .tools import Toolset


GM_SYSTEM_PROMPT = """You are a tabletop RPG Game Master running a solo adventure.
You must keep narration concise and respect the player's safety settings and world tone.
All dice rolls or state changes MUST be done through provided tools; never fabricate numbers.
Respond with vivid narration plus clear next choices when appropriate."""


class SimpleNarrator:
    """Fallback GM behavior when DeepAgents or model access is unavailable."""

    def __init__(self, toolset: Toolset, session: Dict):
        self.toolset = toolset
        self.session = session

    def take_turn(self, player_input: str, selected_choice_id: Optional[str]) -> Dict:
        # 簡易 GM ロジックで 1 ターン分の結果を返す
        log: List[str] = []
        dice_results: List[Dict] = []
        world_diff: Dict = {}
        narration_parts: List[str] = []

        player_input_lower = (player_input or "").lower()
        primary_char = (self.session.get("characters") or [None])[0]

        if not primary_char:
            narration_parts.append("No player character exists yet. Create one to begin the adventure.")
            choices = [
                {"id": "create", "text": "Create a character"},
                {"id": "wait", "text": "Wait"},
            ]
        else:
            if "search" in player_input_lower or "look" in player_input_lower:
                outcome = self.toolset.request_skill_check(primary_char["id"], "perception", 12)
                log.append(outcome.get("detail", "Performed a perception check."))
                dice_results.extend(outcome.get("rolls", []))
                if outcome.get("success"):
                    narration_parts.append("You scour the area and spot a hidden lever beneath some debris.")
                    world_update = self.toolset.update_world_fact("found_lever", True)
                    world_diff.update(world_update.get("updated", {}))
                    choices = [
                        {"id": "pull_lever", "text": "Pull the lever"},
                        {"id": "ignore", "text": "Ignore it for now"},
                    ]
                else:
                    narration_parts.append("You find nothing of note yet; the shadows remain still.")
                    choices = [
                        {"id": "search_again", "text": "Search again"},
                        {"id": "move_on", "text": "Move on cautiously"},
                    ]
            elif "attack" in player_input_lower or "strike" in player_input_lower:
                targets = self.session.get("characters") or []
                target = targets[1] if len(targets) > 1 else None
                if target:
                    outcome = self.toolset.attack_roll(
                        primary_char["id"],
                        target["id"],
                        weapon={"damage": "1d6"},
                    )
                    log.append(outcome.get("detail", "Attack resolved."))
                    dice_results.extend(outcome.get("rolls", []))
                    self.session = services.get_session(self.session["id"]) or self.session
                    narration_parts.append("Steel clashes as you press the attack.")
                else:
                    narration_parts.append("You practice your swings against a worn training dummy.")
                choices = [
                    {"id": "attack_again", "text": "Attack again"},
                    {"id": "pause", "text": "Catch your breath"},
                ]
            else:
                narration_parts.append(
                    "The AI GM considers your action and the world waits expectantly."
                )
                choices = [
                    {"id": "explore", "text": "Explore the next corridor"},
                    {"id": "rest", "text": "Take a short rest"},
                    {"id": "search", "text": "Search the surroundings"},
                ]

        narration = " ".join(narration_parts) or "The story advances."
        state = services.summarize_state(services.get_session(self.session["id"]))
        return {
            "narration": narration,
            "choices": choices,
            "log": log,
            "dice_results": dice_results,
            "world_diff": world_diff,
            "state": state,
            "mode": "simple",
        }


def _build_deep_agent(toolset: Toolset):
    # DeepAgents が有効ならエージェントを生成
    if os.getenv("USE_DEEPAGENTS") not in ("1", "true", "True"):
        return None
    try:
        from deepagents import create_deep_agent
        from langchain.chat_models import init_chat_model
    except Exception:
        return None
    model_name = os.getenv("GM_MODEL", "gpt-4o-mini")
    model = init_chat_model(model=model_name)
    tools = [
        toolset.request_skill_check,
        toolset.attack_roll,
        toolset.query_game_state,
        toolset.update_world_fact,
        toolset.evaluate_rule,
    ]
    return create_deep_agent(model=model, tools=tools, system_prompt=GM_SYSTEM_PROMPT)


class GMAgent:
    # DeepAgents またはフォールバックで GM 振る舞いを提供
    def __init__(self, session: Dict):
        self.session = session
        self.toolset = Toolset(session["id"])
        self.deep_agent = _build_deep_agent(self.toolset)
        self.fallback = SimpleNarrator(self.toolset, session)

    def take_turn(self, player_input: str, selected_choice_id: Optional[str]) -> Dict:
        # Deep agent integration would go here; fallback keeps flow working offline.
        if self.deep_agent:
            try:
                payload = {
                    "messages": [
                        {"role": "system", "content": GM_SYSTEM_PROMPT},
                        {"role": "user", "content": player_input or ""},
                    ]
                }
                response = self.deep_agent.invoke(payload)
                return {
                    "narration": response.get("content", ""),
                    "choices": response.get("choices", []),
                    "log": response.get("log", []),
                    "dice_results": response.get("dice_results", []),
                    "world_diff": response.get("world_diff", {}),
                    "state": services.summarize_state(services.get_session(self.session["id"])),
                    "mode": "deep_agent",
                }
            except Exception as exc:  # fall back on errors
                return {
                    "narration": f"(DeepAgent failed: {exc}) Falling back to simple GM.",
                    "choices": [],
                    "log": [],
                    "dice_results": [],
                    "world_diff": {},
                    "state": services.summarize_state(services.get_session(self.session["id"])),
                    "mode": "deep_agent_error",
                }
        return self.fallback.take_turn(player_input, selected_choice_id)
