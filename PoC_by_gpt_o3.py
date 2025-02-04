"""
TPRG PoC using Swarm

このコードは、実験的なSwarmフレームワークを使って、
・GMエージェント（シナリオ管理、ハンドオフ）、
・戦闘エージェント（ターン制の戦闘計算）、
・キャラクター管理エージェント（キャラ生成）、
・アイテム管理エージェント（アイテムの追加/削除）、
・ワールドエージェント（世界イベント生成）、
・NPCエージェント（NPCとの会話）
の各エージェントが連携して動作するPoC例です。

※本コードはPoC（Proof-of-Concept）としてのサンプルです。
   いつかキャッシュが吹っ飛んでも、全キャラがスライムLv1になっても笑い飛ばせる仕様です！
"""

from swarm import Swarm, Agent
import json
from icecream import ic # デバッグ用

# Swarmクライアントの初期化
client = Swarm()

# ========= 各エージェントで使用するツール関数 =========

def battle_turn(enemy: str, player_hp: int, enemy_hp: int) -> str:
    """
    戦闘エージェント用の関数
    シンプルな固定ダメージ計算：敵に10のダメージを与えます。
    """
    damage = 10
    enemy_hp_after = enemy_hp - damage
    result = f"戦闘結果: {enemy}に{damage}のダメージ。残りHP: {enemy_hp_after}"
    return result

def create_character(name: str, chaos_level: int) -> str:
    """
    キャラクター管理エージェント用の関数
    名前とカオス度（0～100）により初期ステータスを生成します。
    """
    base_hp = 50
    hp = base_hp + chaos_level  # 単純にカオス度を加算
    return f"キャラクター '{name}' が生成されました。HP: {hp}、カオス度: {chaos_level}"

def manage_item(action: str, item: str) -> str:
    """
    アイテム管理エージェント用の関数
    actionは 'add' か 'remove' を指定してください。
    """
    if action == "add":
        return f"アイテム '{item}' をインベントリに追加しました。"
    elif action == "remove":
        return f"アイテム '{item}' をインベントリから削除しました。"
    else:
        return "不明なアクションです。"

def world_event() -> str:
    """
    ワールドエージェント用の関数
    固定の世界イベントを生成します。
    """
    return "世界イベント: 謎の霧が立ち込め、視界が悪化しています。"

def npc_interact(topic: str) -> str:
    """
    NPCエージェント用の関数
    指定されたトピックについての会話をシミュレーションします。
    """
    return f"NPCは '{topic}' について、昔話を始めました。"

# ---------- ハンドオフ用の関数（戻り値がAgentとなる） ----------

def transfer_to_battle() -> Agent:
    """戦闘が必要なとき、戦闘エージェントに転送します。"""
    return battle_agent

def transfer_to_character() -> Agent:
    """キャラクター作成が必要なとき、キャラクター管理エージェントに転送します。"""
    return character_agent

def transfer_to_item() -> Agent:
    """アイテム管理が必要なとき、アイテム管理エージェントに転送します。"""
    return item_agent

def transfer_to_world() -> Agent:
    """世界の状況確認が必要なとき、ワールドエージェントに転送します。"""
    return world_agent

def transfer_to_npc() -> Agent:
    """NPCとの会話が必要なとき、NPCエージェントに転送します。"""
    return npc_agent

def transfer_back_to_gm() -> Agent:
    """処理が完了したら、ゲームマスター（GMエージェント）に戻ります。"""
    return gm_agent

# ========= 各エージェントの定義 =========

# 戦闘エージェント
battle_agent = Agent(
    name="Battle Agent",
    instructions="あなたは戦闘エージェントです。ターン制の戦闘を実施し、シンプルなダメージ計算を行います。",
    functions=[battle_turn]
)

# キャラクター管理エージェント
character_agent = Agent(
    name="Character Agent",
    instructions="あなたはキャラクター管理エージェントです。キャラクターの作成とステータス管理を担当します。",
    functions=[create_character]
)

# アイテム管理エージェント
item_agent = Agent(
    name="Item Agent",
    instructions="あなたはアイテム管理エージェントです。アイテムの追加・削除、管理を行います。",
    functions=[manage_item]
)

# ワールドエージェント
world_agent = Agent(
    name="World Agent",
    instructions="あなたはワールドエージェントです。世界のイベントや環境変化を管理します。",
    functions=[world_event]
)

# NPCエージェント
npc_agent = Agent(
    name="NPC Agent",
    instructions="あなたはNPCエージェントです。NPCとの会話を担当します。",
    functions=[npc_interact]
)

# ゲームマスター（GM）エージェント
gm_agent = Agent(
    name="GM Agent",
    instructions=(
        "あなたはゲームマスターです。TRPGのシナリオを管理し、ユーザーの入力に応じて適切なエージェントにハンドオフします。"
        "探索、戦闘、キャラクター作成、アイテム取得、NPCとの会話、世界イベントなど、状況に合わせて対応してください。"
    ),
    functions=[transfer_to_battle, transfer_to_character, transfer_to_item, transfer_to_world, transfer_to_npc, transfer_back_to_gm]
)

# ========= PoCシミュレーション =========

def run_poc():
    """
    PoCシミュレーションのメインループ
    ユーザーからのメッセージとエージェント間のハンドオフをシミュレーションします。
    """
    messages = []
    # 初回メッセージ：ゲーム開始と探索開始
    messages.append({"role": "user", "content": "ゲームを開始します。探索を始めてください。"})
    
    # 初期はGMエージェントでシナリオ生成
    current_agent = gm_agent
    response = client.run(agent=current_agent, messages=messages)
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # ① 戦闘シナリオに移行：ユーザーが「敵が現れた！」と入力
    messages.append({"role": "user", "content": "突然、敵が現れた！戦闘開始！"})
    response = client.run(agent=current_agent, messages=messages)
    if response.agent.name != current_agent.name:
        current_agent = response.agent
        ic(f"--- ハンドオフ: {current_agent.name} に転送 ---")
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # 戦闘エージェントで戦闘処理（例：敵「ゴブリン」、プレイヤーHP:40、敵HP:30）
    messages.append({"role": "user", "content": "戦闘開始。敵はゴブリン、プレイヤーHPは40、敵HPは30。"})
    response = client.run(agent=current_agent, messages=messages)
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # ② キャラクター作成へ戻る（戦闘後にキャラの強化や再生成を希望）
    messages.append({"role": "user", "content": "戦闘終了。次はキャラクター作成をしたい。"})
    response = client.run(agent=gm_agent, messages=messages)
    if response.agent.name != gm_agent.name:
        current_agent = response.agent
        ic(f"--- ハンドオフ: {current_agent.name} に転送 ---")
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # キャラクター管理エージェントでキャラクター生成
    messages.append({"role": "user", "content": "キャラクター名は『勇者』、カオス度は20で作成してください。"})
    response = client.run(agent=current_agent, messages=messages)
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # ③ アイテム取得シナリオ：探索中にアイテム取得
    messages.append({"role": "user", "content": "探索中に『魔法の剣』を発見しました。"})
    response = client.run(agent=gm_agent, messages=messages)
    if response.agent.name != gm_agent.name:
        current_agent = response.agent
        ic(f"--- ハンドオフ: {current_agent.name} に転送 ---")
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # アイテム管理エージェントでアイテム追加処理
    messages.append({"role": "user", "content": "『魔法の剣』をインベントリに追加してください。"})
    response = client.run(agent=current_agent, messages=messages)
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # ④ 世界イベントの確認：周囲の状況を把握
    messages.append({"role": "user", "content": "次に、現在の世界の状況を教えてください。"})
    response = client.run(agent=gm_agent, messages=messages)
    if response.agent.name != gm_agent.name:
        current_agent = response.agent
        ic(f"--- ハンドオフ: {current_agent.name} に転送 ---")
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # ワールドエージェントで世界イベント生成
    messages.append({"role": "user", "content": "現在の世界イベントは？"})
    response = client.run(agent=current_agent, messages=messages)
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # ⑤ NPCとの会話：NPCエージェントとの対話を実施
    messages.append({"role": "user", "content": "近くのNPCと会話したいです。"})
    response = client.run(agent=gm_agent, messages=messages)
    if response.agent.name != gm_agent.name:
        current_agent = response.agent
        ic(f"--- ハンドオフ: {current_agent.name} に転送 ---")
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # NPCエージェントで会話シミュレーション
    messages.append({"role": "user", "content": "『この町の伝説は何ですか？』と聞いてください。"})
    response = client.run(agent=current_agent, messages=messages)
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")
    
    # 最後に、ゲーム終了・リセット処理（全データが消えれば、全キャラがスライムLv1…かも？）
    messages.append({"role": "user", "content": "全て終了。ゲームをリセットしてください。"})
    response = client.run(agent=gm_agent, messages=messages)
    if response.agent.name != gm_agent.name:
        current_agent = response.agent
        ic(f"--- ハンドオフ: {current_agent.name} に転送 ---")
    ic(f"{current_agent.name}: {response.messages[-1]['content']}")

if __name__ == "__main__":
    run_poc()
