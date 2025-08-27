from __future__ import annotations
from typing import TypedDict, Literal
from typing_extensions import NotRequired # Python 3.10までは typing_extensions から
from langgraph.graph import StateGraph, START, END
import random
from models import SessionBundle


class GState(TypedDict):
    session_id: str
    intent: NotRequired[str]
    decision: NotRequired[Literal["battle","narrate"]]
    message: NotRequired[str]
    dmg_to_player: NotRequired[int]

class GUpdate(TypedDict, total=False):
    # ここは「更新しうるキー」だけ、全部 optional
    session_id: str
    intent: str
    decision: Literal["battle","narrate"]
    message: str
    dmg_to_player: int


def gm_node(state: GState) -> GUpdate:
    '''GMノード：次に何をするか決める（超簡易）'''
    # ここは本来LLMに差し替え。この例では intent 基本 + たまにランダム戦闘
    intent = (state.get("intent") or "explore").lower()
    if intent == "attack":
        decision = "battle"
    else:
        decision = "battle" if random.random() < 0.3 else "narrate"
    return {"decision": decision, "message": "GMは次の展開を決めた。"}


def battle_node(state: GState) -> GUpdate:
    '''バトルノード：ダメージを与えるだけの最小処理'''
    bundle = SessionBundle.redis_load(state["session_id"])
    if not bundle:
        return {"message": "セッションが見つからない", "decision": "battle", "dmg_to_player": 0}

    # シンプル計算：dmg = max(1, char.atk - char.df//2) ± カオス補正
    base = max(1, bundle.character.atk - max(0, bundle.character.df // 2))
    chaos_rate = bundle.character.chaos / 200.0
    if random.random() < chaos_rate:
        base = int(base * random.choice([0.5, 1.5]))

    lost = bundle.character.take_damage(base)
    bundle.battle.logs.append(f"[BATTLE] 敵の攻撃！ {lost} ダメージ")
    if bundle.character.hp <= 0:
        bundle.battle.logs.append("[SYS] あなたは死亡した……（ゲームオーバー）")
    bundle.redis_save()

    return {
        "decision": "battle",
        "message": f"HP {bundle.character.hp}/{bundle.character.hp_max}（{lost} ダメージ）",
        "dmg_to_player": lost,
    }


def narrate_node(state: GState) -> GUpdate:
    '''ナレーノード：探索・雰囲気テキストのダミー'''
    bundle = SessionBundle.redis_load(state["session_id"])
    if not bundle:
        return {"message": "セッションが見つからない", "decision": "narrate"}
    line = random.choice(["森は静かだ…", "遠くでスライムの鳴き声がする。", "道端に奇妙な石碑がある。"])
    bundle.battle.logs.append(f"[NARRATE] {line}")
    bundle.redis_save()
    return {"decision": "narrate", "message": line}


def router(state: GState) -> Literal["battle","narrate"]:
    '''GMの決定に応じて遷移先を返す'''
    return state.get("decision", "narrate")  # デフォはnarrate


def build_graph():
    '''LangGraphアプリを構築して返す'''
    g = StateGraph(GState)
    g.add_node("gm", gm_node)
    g.add_node("battle", battle_node)
    g.add_node("narrate", narrate_node)
    g.add_edge(START, "gm")
    g.add_conditional_edges("gm", router, {"battle": "battle", "narrate": "narrate"})
    g.add_edge("battle", END)
    g.add_edge("narrate", END)
    return g.compile()


# 使い方（app.pyから import して使う想定）
APP = build_graph()

