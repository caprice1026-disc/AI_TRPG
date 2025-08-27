from __future__ import annotations
from flask import Flask, request, jsonify
from config import Config
from models import Session
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
    sess = Session.new(_sid(), name, job, chaos)
    sess.save()
    return jsonify({
        "ok": True,
        "session_id": sess.session_id,
        "char": {"name": sess.char.name, "job": sess.char.job,
                 "hp": sess.char.hp, "hp_max": sess.char.hp_max,
                 "atk": sess.char.atk, "df": sess.char.df, "chaos": sess.char.chaos}
    })

@app.post("/tick")
def tick():
    '''LangGraphを1ステップだけ動かす（intentに応じて展開）'''
    body = request.get_json(silent=True) or {}
    intent = (body.get("intent") or "explore").lower()
    state: GState = {"session_id": _sid(), "intent": intent}
    out = APP.invoke(state)
    # 直近ログも少し返す
    sess = Session.load(_sid())
    logs = sess.logs[-6:] if sess else []
    return jsonify({
        "message": out.get("message"),
        "decision": out.get("decision"),
        "hp": sess.char.hp if sess else None,
        "hp_max": sess.char.hp_max if sess else None,
        "logs": logs,
    })

# 実行: FLASK_APP=app.py flask run
if __name__ == "__main__":
    app.run(debug=True)