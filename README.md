# AI Solo TRPG (PoC)
Flask ベースのソロ TRPG サーバー兼簡易 Web クライアント。AI GM には Deep Agents（LangChain/LangGraph）を想定しつつ、手元だけでも動くフォールバック GM を備えた Proof of Concept です。要件は `youken.txt` のドラフトに沿って進めています。

## いまの状態
- Python + Flask + SQLite（`trpg.db`）でセッション・キャラクター・ログを保存
- GM ターンは `trpg_app/gm_agent.py` で処理し、`USE_DEEPAGENTS=1` 環境変数がある場合は deepagents + LangChain モデルを使用（未設定時は簡易ナレーターでオフライン動作）
- ルール/ダイス評価はサーバー側で確定させる方針（`trpg_app/dice.py`, `trpg_app/rules.py`）
- シングルページの最小 UI を `static/` に同梱（セッション作成・PC 作成・GM チャット・簡易ダイス）
- 要件ドラフト (`youken.txt`) の P0 項目に相当する部分を中心に実装済み（セッション作成、PC 作成、ダイスロール、GM ターン、ログ保管など）。戦闘トラッカーや長期メモリなど P1+ は未着手。

## セットアップ
1. Python 3.11 以上を準備  
2. 依存インストール
   ```bash
   pip install -r requirements.txt
   # Deep Agents を使う場合は別途
   pip install deepagents langchain
   ```
3. 起動
   ```bash
   python app.py
   # http://localhost:5000 で UI / API を利用
   ```

主要な環境変数:
- `TRPG_DB_PATH` … SQLite のパス（デフォルト: `trpg.db`）
- `USE_DEEPAGENTS` … `1` で Deep Agents を有効化。未設定ならフォールバック GM のみ。
- `GM_MODEL` … Deep Agents 使用時のモデル名（デフォルト: `gpt-4o-mini`）

## API ざっくり
- `POST /api/session` — セッション作成（`name`, `settings`, `safety` 任意）
- `GET /api/session/{id}` — セッション取得（キャラ・ログ含む）
- `POST /api/character` — キャラクター作成（`session_id`, `name` 必須）
- `PUT /api/character/{id}` — キャラクター更新
- `POST /api/dice/roll` — ダイスロール（式は `NdX`、加算、優劣・高低取りなど `trpg_app/dice.py` 参照）
- `POST /api/gm/turn` — GM 1 ターン進行（`session_id` と `player_input` または `selected_choice_id`）
- `GET /api/health` — 動作確認

## ファイル案内
- `app.py` … Flask エントリーポイント
- `trpg_app/db.py` … SQLite 初期化とセッション管理
- `trpg_app/models.py` … ORM モデル（Session / Character / TurnLog / DiceLog）
- `trpg_app/services.py` … セッション / キャラ CRUD、ログ保存、状態サマリ
- `trpg_app/dice.py` / `trpg_app/rules.py` … ダイス式評価と簡易ルール判定
- `trpg_app/gm_agent.py` … Deep Agents 連携とフォールバック GM
- `trpg_app/tools.py` … GM から呼ぶ TRPG 用ツール群（skill check, attack, world fact 更新など）
- `static/` … 簡易ブラウザ UI（`index.html`, `main.js`）

## youken.txt ドラフトとの対応
- P0（Phase 1 想定）: セッション作成/セーブ、PC 作成、ダイスロール API、GM ターン API、判定ログ保存、最低限のセーフティ設定パラメータをサポート。
- 未実装・これから: 長期メモリバックエンド（/memories）、Deep Agents の計画系サブエージェント、戦闘トラッカー、コンペンディウム、X-Card、リプレイエクスポートなど P1+ 項目。
- ルール処理は「AI はダイスを偽造せず、Python ツール経由で行う」方針を踏襲。

## 開発メモ
- Deep Agents を試す場合は `USE_DEEPAGENTS=1` を設定し、モデル提供元の環境変数（例: `OPENAI_API_KEY`）も合わせて用意してください。
- ルール拡張や DSL 化は `trpg_app/rules.py` を起点に追加する想定です。
