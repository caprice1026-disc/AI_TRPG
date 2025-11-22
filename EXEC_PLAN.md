# Phase 1 MVP: AI Solo TRPG (Flask + DeepAgents-friendly core)

This ExecPlan is a living document. Keep `Progress`, `Surprises & Discoveries`, `Decision Log`, and `Outcomes & Retrospective` up to date as work proceeds. Follow the repository guidance in `PLANS.md` when editing this file.

## Purpose / Big Picture

Deliver a minimal but playable solo TRPG web app where a user can create a session, define a character, roll dice with logging, and exchange turns with an AI GM endpoint that routes all rules through server-side tools. After implementation, a user should be able to start the Flask server, open the HTML UI, create a session/character, chat with the GM, see HP/state updates, and reload the session later via its ID.

## Progress

- [x] (2025-11-21 13:40Z) Drafted initial ExecPlan covering Phase 1 scope, architecture, and validation.
- [x] (2025-11-21 18:25Z) Implemented backend core (Flask app scaffold, SQLite schema, dice engine, rule helpers, TRPG tools, DeepAgents-friendly adapter stub).
- [x] (2025-11-21 18:32Z) Exposed REST endpoints for session, character, dice roll, and GM turn with persistence and logging.
- [x] (2025-11-21 18:36Z) Built minimal HTML/JS front-end chat + status panel consuming the APIs.
- [x] (2025-11-21 18:45Z) Wired AI GM turn flow (fallback narrator) with logging; smoke-tested via services module.
- [x] (2025-11-21 18:55Z) Documented run/test steps and recorded current outcomes/next gaps.

## Surprises & Discoveries

- None yet.
- Observation: Directly calling `services.create_session` outside the Flask app failed before DB init. Fixed by calling `db.init_db()` on module import so tests and scripts work without the app entrypoint.  
  Evidence: services-level smoke test now creates a session, character, and GM response successfully.

## Decision Log

- Decision: Use SQLite via Python stdlib for persistence with JSON blobs for flexible game state; keep schema simple to accelerate MVP.  
  Rationale: Matches requirement for SQLite PoC, minimizes dependencies while allowing future refactors to ORMs.  
  Date/Author: 2025-11-21 / Codex
- Decision: Provide DeepAgents integration point with graceful fallback stub when the library/model key is missing.  
  Rationale: Allows end-to-end flow and tooling contract without blocking on model access during local PoC.  
  Date/Author: 2025-11-21 / Codex
- Decision: Migrate persistence to SQLAlchemy ORM with JSON text fields instead of raw SQL.  
  Rationale: Improves maintainability and type safety while retaining SQLite compatibility and JSON payload flexibility.  
  Date/Author: 2025-11-22 / Codex

## Outcomes & Retrospective

Phase 1 MVP scaffolding now runs end-to-end: Flask serves the API and static UI, SQLite persists sessions/characters/logs, the dice engine handles NdX arithmetic plus adv/kh/kl, and the GM turn flow works via the simple narrator fallback. Manual smoke tests through the services module confirmed session creation, character creation, and a search action with logged rolls. Remaining gaps include richer DeepAgents-driven narration once a model/key is available and broader rule coverage/automated tests, but the current build allows a solo dungeon crawl loop to function.

## Context and Orientation

Current repo is empty aside from this plan and source requirement text (`youken.txt`). We will create a Python package-based Flask app with a lightweight SQLite database file in the repo root (`trpg.db`). Key planned files:
- `app.py`: Flask entry point (serves API + static front-end).
- `trpg_app/` package: `__init__.py`, `db.py` (connection + migrations), `models.py` (schema helper), `dice.py` (roller), `rules.py` (Skill/Attack/Save evaluation + DSL), `tools.py` (TRPG tool functions exposed to agent), `gm_agent.py` (DeepAgents adapter + stub), `services.py` (session/character/game state helpers).
- `static/index.html` and `static/main.js`: barebones front-end chat/status UI.
- `requirements.txt`: dependencies (Flask, its extras; optional DeepAgents/LangChain noted).

## Plan of Work

Lay foundations first, then layer features to keep the system runnable at each step. Start by scaffolding the package and dependency list. Build SQLite initialization with tables for sessions, characters, world state, and logs (turn logs + dice logs) and helper functions to load/save JSON blobs. Implement a deterministic dice engine supporting NdX arithmetic, parentheses, advantage/disadvantage (`adv(expr)`, `dis(expr)`), and keep-high/keep-low (`kh`/`kl` suffix on dice). Add rule helpers for Skill/Attack/Save using the dice engine; compute derived stats (ability modifiers, AC). Implement TRPG tool functions that wrap these rules and mutate stored session/character state while logging events.

Next, create a DeepAgents adapter that tries to import and configure `create_deep_agent` with a system prompt and registered tools; if unavailable, fall back to a simple rule-based narrator that echoes player input, triggers default checks, and surfaces tool outputs. Build Flask endpoints for session creation/retrieval, character create/update, dice roll, and GM turn. Ensure GM turn reads the session, calls the agent, applies tool results, logs narration/dice/events, and returns updated state summaries and choices.

Finally, deliver a minimal static front-end: a single-page HTML served by Flask that allows entering a session ID or creating one, editing a character, sending chat messages, and seeing narration/logs/state updates. Add basic styling and client-side fetch helpers. Document how to run the server, seed a sample session, and exercise the flow.

## Concrete Steps

1. From repo root, create a virtualenv and install dependencies. Example (PowerShell):
      python -m venv .venv
      .\.venv\Scripts\Activate.ps1
      pip install -r requirements.txt
2. Initialize the Flask app (`python app.py`) which will auto-create `trpg.db` if missing.
3. In a browser, open `http://127.0.0.1:5000/` to access the UI.
4. Create a new session via the UI or `curl`:
      curl -X POST http://127.0.0.1:5000/api/session -H "Content-Type: application/json" -d "{\"name\":\"demo\",\"safety\":{\"violence\":\"low\"}}"
5. Create a character for that session:
      curl -X POST http://127.0.0.1:5000/api/character -H "Content-Type: application/json" -d "{\"session_id\":\"<id>\",\"name\":\"Aria\",\"race\":\"human\",\"clazz\":\"fighter\",\"level\":1,\"base_stats\":{\"STR\":16,\"DEX\":12,\"CON\":14,\"INT\":10,\"WIS\":10,\"CHA\":8},\"skills\":{\"perception\":2},\"resources\":{\"hp\":12}}"
6. Roll dice:
      curl -X POST http://127.0.0.1:5000/api/dice/roll -H "Content-Type: application/json" -d "{\"expression\":\"1d20+5\"}"
7. Send a GM turn request:
      curl -X POST http://127.0.0.1:5000/api/gm/turn -H "Content-Type: application/json" -d "{\"session_id\":\"<id>\",\"player_input\":\"I search the room\"}"
8. Observe responses and verify logs via `GET /api/session/<id>`.

Update these commands if file paths or ports change during implementation.

## Validation and Acceptance

The system is accepted when the Flask server starts without errors, and a user can create a session, add a character, roll dice with detailed breakdowns, and complete at least one GM turn that returns narration, choices, a log of events, and an updated state summary. Validation steps:
- Run `python app.py`; expect console output indicating the server is serving on `http://127.0.0.1:5000`.
- Hit `POST /api/dice/roll` with `adv(d20+3)` and observe JSON containing `total`, `breakdown`, and `rolls` with two d20 results and the chosen one.
- Create a session + character, then call `POST /api/gm/turn` and verify the response includes `narration`, `state.hp`, `choices` array, and `log` entries; `turn_logs` in the DB should append.
- Load the front-end page, chat once, refresh the browser, and confirm the session ID reloaded state via `GET /api/session/<id>`.

## Idempotence and Recovery

Database initialization checks for tables and only creates them if missing; rerunning `python app.py` is safe. API calls are additive (creating new sessions/characters) and updates are scoped by IDs. If the DB becomes corrupted, delete `trpg.db` to reinitialize (session data will be lost). Dice rolls and logs are append-only; rerolling simply adds more logs.

## Artifacts and Notes

- `trpg.db` will be created in the repo root on first run.
- Static assets live under `static/` and are served by Flask without extra config.
- DeepAgents usage is optional; the adapter will fall back if the libraries/models are unavailable, but the code path remains ready for production keys.

## Interfaces and Dependencies

- Dependencies (to be listed in `requirements.txt`): `Flask`, `Flask-Cors` (if needed), and `python-dotenv` optional for env vars; optional `deepagents` and `langchain` can be installed when model access is available.
- Core interfaces:
  - Dice roller (`trpg_app.dice.roll(expression: str) -> {total:int, rolls:list, breakdown:str}`) supporting NdX arithmetic, adv/dis, kh/kl.
  - Rule evaluator (`trpg_app.rules.request_skill_check(actor, skill, dc)`, `attack_roll(attacker, target)`, `saving_throw(actor, dc, save_type)`).
  - TRPG tools (`trpg_app.tools` functions) mutate state and log outcomes; agent uses them exclusively for rules effects.
  - GM adapter (`trpg_app.gm_agent.GMAgent`) exposes `take_turn(session, player_input, selected_choice_id=None)` returning narration, choices, logs, and updated state.
- Flask endpoints:
  - `POST /api/session` create; `GET /api/session/<id>` retrieve.
  - `POST /api/character`, `PUT /api/character/<id>`.
  - `POST /api/dice/roll`.
  - `POST /api/gm/turn`.
