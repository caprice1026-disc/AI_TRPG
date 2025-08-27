from __future__ import annotations
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, START, END
import random
from models import Session

class GState(TypedDict, total=False):
    '''LangGraphの共有状態（最小）'''
    session_id: str
    intent: str            # 例: "start" / "attack" / "explore"
    decision: Literal["battle","narrate"]
    message: str           # ユーザへ返すテキスト（要約/演出）
    dmg_to_player: int

def gm_node(state: GState) -> GState:
    '''GMノード：次に何をするか決める（超簡易）'''
    # ここは本来LLMに差し替え。この例では intent 基本 + たまにランダム戦闘
    intent = (state.get("intent") or "explore").lower()
    if intent == "attack":
        decision = "battle"
    else:
        decision = "battle" if random.random() < 0.3 else "narrate"
    return {"decision": decision, "message": "GMは次の展開を決めた。"}

def battle_node(state: GState) -> GState:
    '''バトルノード：ダメージを与えるだけの最小処理'''
    sid = state.get("session_id")
    if not sid:
        return {"message": "セッションID未指定", "decision": "battle", "dmg_to_player": 0}
    sess = Session.load(sid)
    if not sess:
        return {"message": "セッションが見つからない", "decision": "battle", "dmg_to_player": 0}

    # シンプル計算：dmg = max(1, char.atk - char.df//2) ± カオス補正
    base = max(1, sess.char.atk - max(0, sess.char.df // 2))
    chaos_rate = sess.char.chaos / 200.0
    if random.random() < chaos_rate:
        base = int(base * random.choice([0.5, 1.5]))

    lost = sess.char.take_damage(base)
    sess.logs.append(f"[BATTLE] 敵の攻撃！ {lost} ダメージ")
    if sess.char.hp <= 0:
        sess.logs.append("[SYS] あなたは死亡した……（ゲームオーバー）")
    sess.save()

    return {
        "decision": "battle",
        "message": f"HP {sess.char.hp}/{sess.char.hp_max}（{lost} ダメージ）",
        "dmg_to_player": lost
    }

def narrate_node(state: GState) -> GState:
    '''ナレーノード：探索・雰囲気テキストのダミー'''
    sid = state.get("session_id")
    if not sid:
        return {"message": "セッションID未指定", "decision": "narrate"}
    sess = Session.load(sid)
    if not sess:
        return {"message": "セッションが見つからない", "decision": "narrate"}
    line = random.choice(["森は静かだ…", "遠くでスライムの鳴き声がする。", "道端に奇妙な石碑がある。"])
    sess.logs.append(f"[NARRATE] {line}")
    sess.save()
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
