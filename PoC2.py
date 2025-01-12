from swarm import Swarm, Agent
from icecream import ic # デバッグ用
from swarm.repl import run_demo_loop

client = Swarm()

def transer_to_GM_agent():
    return GameMaster_agent

def transer_to_Tactics_agent():
    return Tactics_agent

GameMaster_agent = Agent(
    name="GameMaster",
    instructions="""あなたはTRPGのゲームマスターとして、プレイヤーとのやり取りを担当します。
    プレイヤーの名前は、{name}さんです。{name}さんのキャラクタークラスは、{character_class}です。
    彼には、{back_story}というバックストーリーがあります。
    彼の入力をもとに、各エージェントに指示を出し、ストーリーを進めてください。また、エージェントから帰ってきた結果をもとに
    プレイヤーに情報を伝えてください。
    """,
    functions=[transer_to_Tactics_agent],
)

Tactics_agent = Agent(
    name="Tactics",
    instructions="""あなたは、TRPGのゲームにおいて、戦闘部分のストーリーを紡ぐエージェントです。
    入力をもとに、戦闘の展開を考え、GameMasterに内容を伝えてください。
    """,
    functions=[transer_to_GM_agent],
)

print("-------------------------------------")
for f in GameMaster_agent.functions:
    print(f.__name__)
print("-------------------------------------")

if __name__ == "__main__":
    # デモループの実行
    run_demo_loop(GameMaster_agent, debug=False)