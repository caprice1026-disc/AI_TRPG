import os
from pathlib import Path
from typing import Any, Dict

from flask import Flask, jsonify, request, send_from_directory

from trpg_app import db, dice, gm_agent, services


app = Flask(__name__, static_folder="static", static_url_path="")
db.init_db()


def _json_error(message: str, status: int = 400):
    # エラーレスポンスを組み立てるヘルパ
    return jsonify({"error": message}), status


@app.route("/")
def index():
    # フロントのシングルページを返却
    index_path = Path(app.static_folder) / "index.html"
    if index_path.exists():
        return send_from_directory(app.static_folder, "index.html")
    return jsonify({"message": "TRPG server running; static UI not found"}), 200


@app.route("/api/health")
def health():
    # 動作確認用ヘルスチェック
    return jsonify({"status": "ok"})


@app.route("/api/session", methods=["POST"])
def create_session():
    # セッション作成 API
    payload = request.get_json(force=True, silent=True) or {}
    session = services.create_session(
        name=payload.get("name"),
        settings=payload.get("settings"),
        safety=payload.get("safety"),
    )
    return jsonify(session), 201


@app.route("/api/session/<session_id>", methods=["GET"])
def get_session(session_id: str):
    # セッション取得 API
    session = services.get_session(session_id)
    if not session:
        return _json_error("session not found", 404)
    return jsonify(session)


@app.route("/api/character", methods=["POST"])
def create_character():
    # キャラクター作成 API
    payload = request.get_json(force=True, silent=True) or {}
    required_fields = ["session_id", "name"]
    missing = [f for f in required_fields if f not in payload]
    if missing:
        return _json_error(f"missing fields: {', '.join(missing)}")
    if not services.get_session(payload["session_id"]):
        return _json_error("session not found", 404)
    character = services.create_character(
        session_id=payload["session_id"],
        name=payload["name"],
        race=payload.get("race", ""),
        clazz=payload.get("clazz", ""),
        level=int(payload.get("level", 1)),
        base_stats=payload.get("base_stats") or {},
        skills=payload.get("skills") or {},
        resources=payload.get("resources") or {},
    )
    return jsonify(character), 201


@app.route("/api/character/<char_id>", methods=["PUT"])
def update_character(char_id: str):
    # キャラクター更新 API
    payload = request.get_json(force=True, silent=True) or {}
    updated = services.update_character(char_id, payload)
    if not updated:
        return _json_error("character not found", 404)
    return jsonify(updated)


@app.route("/api/dice/roll", methods=["POST"])
def roll_dice():
    # ダイスロール API
    payload = request.get_json(force=True, silent=True) or {}
    expr = payload.get("expression")
    session_id = payload.get("session_id")
    if not expr:
        return _json_error("expression is required")
    try:
        result = dice.roll(expr)
    except Exception as exc:
        return _json_error(str(exc))
    services.log_dice(session_id, expr, result)
    return jsonify(result)


def _update_messages(session, player_input: str, gm_text: str):
    # セーブ用メッセージ履歴を更新
    save_blob = dict(session.get("save_blob") or {})
    messages = list(save_blob.get("messages") or [])
    messages.append({"role": "user", "content": player_input})
    messages.append({"role": "assistant", "content": gm_text})
    save_blob["messages"] = messages[-50:]  # keep it short for PoC
    services.update_session_save(session["id"], save_blob)


@app.route("/api/gm/turn", methods=["POST"])
def gm_turn():
    # GM ターン API
    payload: Dict[str, Any] = request.get_json(force=True, silent=True) or {}
    session_id = payload.get("session_id")
    if not session_id:
        return _json_error("session_id is required")
    session = services.get_session(session_id)
    if not session:
        return _json_error("session not found", 404)
    player_input = payload.get("player_input", "")
    selected_choice_id = payload.get("selected_choice_id")
    agent = gm_agent.GMAgent(session)
    response = agent.take_turn(player_input, selected_choice_id)
    turn_no = len(session.get("turn_logs", [])) + 1
    services.log_turn(
        session_id=session_id,
        turn_no=turn_no,
        player_input=player_input,
        gm_output={
            "narration": response.get("narration"),
            "choices": response.get("choices"),
            "log": response.get("log"),
            "mode": response.get("mode"),
        },
        dice_results=response.get("dice_results", []),
        world_diff=response.get("world_diff", {}),
    )
    _update_messages(session, player_input, response.get("narration", ""))
    return jsonify(response)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
