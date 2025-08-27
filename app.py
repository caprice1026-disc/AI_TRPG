from __future__ import annotations
from flask import Flask, request, jsonify
from config import Config
from models import SessionBundle
from graph import APP, GState

app = Flask(__name__)
app.config.from_object(Config)

def _sid() -> str:
    '''セッションIDを取得（未ログイン前提なので雑でOK）'''
    sid = request.cookies.get("sid") or request.headers.get("X-Session") or "debug-session"
    return sid

@app.post("/start")
def start():
    '''新規セッション作成'''
    body = request.get_json(silent=True) or {}
    name  = body.get("name", "勇者")
    job   = body.get("job", "戦士")
    chaos = int(body.get("chaos", 0))
    bundle = SessionBundle.new_session(_sid(), name, job, chaos)
    bundle.redis_save()
    return jsonify({
        "ok": True,
        "session_id": bundle.session_id,
        "char": {"name": bundle.character.name, "job": bundle.character.job,
                 "hp": bundle.character.hp, "hp_max": bundle.character.hp_max,
                 "atk": bundle.character.atk, "df": bundle.character.df, "chaos": bundle.character.chaos}
    })

@app.post("/tick")
def tick():
    '''LangGraphを1ステップだけ動かす（intentに応じて展開）'''
    body = request.get_json(silent=True) or {}
    intent = (body.get("intent") or "explore").lower()
    state: GState = {"session_id": _sid(), "intent": intent}
    out = APP.invoke(state)
    # 直近ログも少し返す
    bundle = SessionBundle.redis_load(_sid())
    logs = bundle.battle.logs[-6:] if bundle else []
    return jsonify({"message": out.get("message"), "decision": out.get("decision"),
                    "hp": bundle.character.hp if bundle else None,
                    "hp_max": bundle.character.hp_max if bundle else None,
                    "logs": logs})

# 実行: FLASK_APP=app.py flask run
if __name__ == "__main__":
    app.run(debug=True)
