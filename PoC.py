from swarm import Swarm, Agent
from icecream import ic # デバッグ用

client = Swarm()

def instructions(context_variables):
    # コンテキスト変数から名前を取得し、指示を生成
    name = context_variables.get("name", "ユーザー")
    character_class = context_variables.get("character_class", None)
    back_story = context_variables.get("back_story", None)
    return f"名前（{name}）とクラス（{character_class}）を持つキャラクターのバックストーリーを作成してください。バックストーリー：{back_story}"

# エージェントの設定
agent = Agent(
    name="Agent",
    instructions=instructions,
)

# コンテキスト変数の設定
context_variables = {
    "name": "John Doe",
    "character_class": "名もなき者",
    "back_story": "ある日、彼は目を覚ましました。彼は何も覚えていませんでした。彼は名もない者でした。",
    "level": 1,
  
}

# アカウント詳細の出力を実行
response = client.run(
    messages=[{"role": "user", "content": "与えられた情報をもとにストーリーを作ってください"}],
    agent=agent,
    context_variables=context_variables,
)
ic(response.messages[-1]["content"])