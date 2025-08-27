# models.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import redis


# =========================
# Redis 接続ユーティリティ
# =========================

def get_redis() -> redis.Redis:
    '''Redis クライアントを返す'''
    # 環境変数から接続先を取得。未設定ならローカルを使用
    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    db = int(os.getenv("REDIS_DB", "0"))
    return redis.Redis(host=host, port=port, db=db, decode_responses=True)


# キーのプレフィックス（同一Redisを他用途と共用しても衝突しにくくする）
REDIS_NS = os.getenv("GAME_REDIS_NS", "trpg")
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "60*60*24"))  # デフォ1日


def rkey(*parts: str) -> str:
    '''名前空間付きのRedisキーを作る'''
    return ":".join([REDIS_NS, *parts])


# =========================
# ゲーム用の基本定義
# =========================

class ItemType(str, Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    CONSUMABLE = "consumable"


def roll_6d2(rng: random.Random) -> int:
    '''6D2（2面ダイスを6回振った合計）を返す'''
    # 1〜2を6回、合計は6〜12
    return sum(rng.randint(1, 2) for _ in range(6))


def clamp(v: int, lo: int, hi: int) -> int:
    '''値を範囲内にクランプする'''
    return max(lo, min(hi, v))


# =========================
# モデル: アイテム / インベントリ
# =========================

@dataclass
class Item:
    # アイテムの基本情報
    id: str
    name: str
    type: ItemType
    # 効果量（武器=攻撃補正, 防具=防御補正, 回復=回復量）
    value: int = 0
    # テキスト説明（GPTのノリで増える可能性あり）
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        '''辞書へシリアライズする'''
        d = asdict(self)
        d["type"] = self.type.value
        return d

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Item":
        '''辞書からItemを復元する'''
        return Item(
            id=d["id"],
            name=d["name"],
            type=ItemType(d["type"]),
            value=int(d.get("value", 0)),
            description=d.get("description", ""),
        )


@dataclass
class Inventory:
    # 所持品リスト
    items: List[Item] = field(default_factory=list)
    # 上限は要件通り10個
    max_size: int = 10

    def to_dict(self) -> Dict[str, Any]:
        '''辞書へシリアライズする'''
        return {"items": [it.to_dict() for it in self.items], "max_size": self.max_size}

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Inventory":
        '''辞書からInventoryを復元する'''
        items = [Item.from_dict(x) for x in d.get("items", [])]
        return Inventory(items=items, max_size=int(d.get("max_size", 10)))

    def add(self, item: Item) -> bool:
        '''インベントリにアイテムを追加する（成功可否を返す）'''
        # 上限超過チェック
        if len(self.items) >= self.max_size:
            return False
        self.items.append(item)
        return True

    def remove_by_id(self, item_id: str) -> Optional[Item]:
        '''ID一致のアイテムをインベントリから削除し、削除したアイテムを返す'''
        for i, it in enumerate(self.items):
            if it.id == item_id:
                return self.items.pop(i)
        return None

    def get_summary(self) -> List[Tuple[str, str]]:
        '''UI表示用に (id, name) の一覧を返す'''
        return [(it.id, it.name) for it in self.items]


# =========================
# モデル: キャラクター
# =========================

@dataclass
class Character:
    # ゲーム内識別子（セッション単位で1キャラ前提）
    id: str
    name: str
    job: str
    chaos: int  # 0〜100
    level: int = 1

    # 能力値
    hp: int = 0
    hp_max: int = 0
    atk: int = 0
    df: int = 0
    agi: int = 0
    intel: int = 0
    luk: int = 0

    # セーブ時刻（メタ情報）
    updated_at: float = field(default_factory=lambda: time.time())

    @staticmethod
    def create_new(char_id: str, name: str, job: str, chaos: int, rng: Optional[random.Random] = None) -> "Character":
        '''新規キャラクターを作成して返す（初期ステは6D2、HPのみ独自計算）'''
        rng = rng or random.Random()
        chaos = clamp(int(chaos), 0, 100)

        # 体力以外は6D2で決定
        atk = roll_6d2(rng)
        df = roll_6d2(rng)
        agi = roll_6d2(rng)
        intel = roll_6d2(rng)
        luk = roll_6d2(rng)

        # HPは「10 + df + agi」ぐらいのゆるい式にしておく（好きに変えてOK）
        hp_max = 10 + df + agi
        hp = hp_max

        return Character(
            id=char_id,
            name=name,
            job=job,
            chaos=chaos,
            level=1,
            hp=hp,
            hp_max=hp_max,
            atk=atk,
            df=df,
            agi=agi,
            intel=intel,
            luk=luk,
        )

    def to_dict(self) -> Dict[str, Any]:
        '''辞書へシリアライズする'''
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Character":
        '''辞書からCharacterを復元する'''
        return Character(**d)

    def is_dead(self) -> bool:
        '''HPが0以下かどうかを返す'''
        return self.hp <= 0

    def heal(self, amount: int) -> int:
        '''HPを回復し、実際に回復した量を返す'''
        before = self.hp
        self.hp = clamp(self.hp + int(amount), 0, self.hp_max)
        return self.hp - before

    def take_damage(self, amount: int) -> int:
        '''ダメージを受け、実際に減ったHP量を返す'''
        before = self.hp
        self.hp = clamp(self.hp - int(amount), 0, self.hp_max)
        return before - self.hp

    def level_up(self) -> None:
        '''レベルアップ：全パラメータ+2（要件どおり）'''
        self.level += 1
        self.hp_max += 2
        self.atk += 2
        self.df += 2
        self.agi += 2
        self.intel += 2
        self.luk += 2
        # HPも素直に2回復（最大値が上がるだけだと悲しいため）
        self.hp = clamp(self.hp + 2, 0, self.hp_max)
        self.updated_at = time.time()


# =========================
# モデル: バトル状態
# =========================

@dataclass
class Enemy:
    # 敵の簡易モデル（GPTが生成する想定）
    name: str
    hp: int
    atk: int
    df: int
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        '''辞書へシリアライズする'''
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "Enemy":
        '''辞書からEnemyを復元する'''
        return Enemy(**d)


@dataclass
class BattleState:
    # 現在の敵（いなければNone）
    enemy: Optional[Enemy] = None
    # ターン数
    turn: int = 0
    # バトルログ（UI側で整形表示）
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        '''辞書へシリアライズする'''
        return {
            "enemy": self.enemy.to_dict() if self.enemy else None,
            "turn": self.turn,
            "logs": list(self.logs),
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "BattleState":
        '''辞書からBattleStateを復元する'''
        enemy = Enemy.from_dict(d["enemy"]) if d.get("enemy") else None
        return BattleState(enemy=enemy, turn=int(d.get("turn", 0)), logs=list(d.get("logs", [])))

    def compute_damage(self, atk: int, df: int, chaos: int, rng: Optional[random.Random] = None) -> Tuple[int, Dict[str, Any]]:
        '''与ダメージを計算し、(最終ダメージ, 補足情報) を返す'''
        rng = rng or random.Random()
        base = max(0, atk - df)

        # クリティカル 5%（ダメ2倍）
        critical = rng.random() < 0.05
        dmg = base * (2 if critical else 1)

        # カオス補正：カオス/200の確率で +50% または -50% をランダム適用
        chaos_rate = clamp(chaos, 0, 100) / 200.0
        chaos_trigger = rng.random() < chaos_rate
        chaos_sign = 0
        if chaos_trigger and dmg > 0:
            chaos_sign = rng.choice([-1, 1])  # -1=減衰, +1=増幅
            dmg = int(dmg * (1.5 if chaos_sign > 0 else 0.5))

        return max(0, dmg), {
            "critical": critical,
            "chaos_trigger": chaos_trigger,
            "chaos_sign": chaos_sign,  # -1 / 0 / +1
            "base": base,
        }

    def attack_player(self, player: Character, rng: Optional[random.Random] = None) -> int:
        '''敵がプレイヤーを攻撃する（与えたダメージを返す）'''
        if not self.enemy:
            return 0
        dmg, meta = self.compute_damage(self.enemy.atk, player.df, player.chaos, rng)
        lost = player.take_damage(dmg)
        self.logs.append(self._fmt_log(f"{self.enemy.name} の攻撃！ {lost} ダメージ"))
        if meta["critical"]:
            self.logs.append(self._fmt_log("クリティカル！"))
        if meta["chaos_trigger"]:
            self.logs.append(self._fmt_log("カオスの風が吹いた…（ダメージ補正）"))
        return lost

    def attack_enemy(self, player: Character, rng: Optional[random.Random] = None) -> int:
        '''プレイヤーが敵を攻撃する（与えたダメージを返す）'''
        if not self.enemy:
            return 0
        dmg, meta = self.compute_damage(player.atk, self.enemy.df, player.chaos, rng)
        self.enemy.hp = max(0, self.enemy.hp - dmg)
        self.logs.append(self._fmt_log(f"{player.name} の攻撃！ {dmg} ダメージ"))
        if meta["critical"]:
            self.logs.append(self._fmt_log("クリティカル！"))
        if meta["chaos_trigger"]:
            self.logs.append(self._fmt_log("カオスの風が吹いた…（ダメージ補正）"))
        return dmg

    def _fmt_log(self, text: str) -> str:
        '''バトルログの整形（タイムスタンプ入りの簡易版）'''
        ts = time.strftime("%H:%M:%S", time.localtime())
        return f"[{ts}] {text}"


# =========================
# モデル: ゲーム全体状態
# =========================

@dataclass
class GameState:
    # シナリオIDやフラグ類（実装初期はゆるく適当でOK）
    scenario_id: Optional[str] = None
    last_event: Optional[str] = None
    game_over: bool = False

    def to_dict(self) -> Dict[str, Any]:
        '''辞書へシリアライズする'''
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "GameState":
        '''辞書からGameStateを復元する'''
        return GameState(**d)


@dataclass
class AgentMessage:
    # Swarmエージェント用の軽量ログ（GM/BA/CA/IA/WA/NPC）
    agent: str
    role: str  # "system" / "user" / "assistant"
    content: str
    ts: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> Dict[str, Any]:
        '''辞書へシリアライズする'''
        return asdict(self)

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "AgentMessage":
        '''辞書からAgentMessageを復元する'''
        return AgentMessage(**d)


@dataclass
class SessionBundle:
    # 1セッション=1キャラ前提のまとめ
    session_id: str
    character: Character
    inventory: Inventory
    game: GameState
    battle: BattleState = field(default_factory=BattleState)
    # 直近のエージェントメッセージ（UIでダイジェスト表示）
    agent_messages: List[AgentMessage] = field(default_factory=list)

    # --------- 永続化系（Redis） ---------

    def redis_save(self, r: Optional[redis.Redis] = None, ex: Optional[int] = SESSION_TTL_SECONDS) -> None:
        '''現在のセッション状態をRedisへ保存する'''
        r = r or get_redis()
        data = {
            "character": self.character.to_dict(),
            "inventory": self.inventory.to_dict(),
            "game": self.game.to_dict(),
            "battle": self.battle.to_dict(),
            "agent_messages": [m.to_dict() for m in self.agent_messages][-50:],  # 直近50件だけ保存
        }
        # まとめて保存。TTLを付与しておく（放置セッション掃除用）
        r.set(rkey("session", self.session_id), json.dumps(data, ensure_ascii=False), ex=ex)

    @staticmethod
    def redis_load(session_id: str, r: Optional[redis.Redis] = None) -> Optional["SessionBundle"]:
        '''Redisからセッション状態を読み込む（なければNone）'''
        r = r or get_redis()
        raw = r.get(rkey("session", session_id))
        if not raw:
            return None
        d = json.loads(raw)
        bundle = SessionBundle(
            session_id=session_id,
            character=Character.from_dict(d["character"]),
            inventory=Inventory.from_dict(d["inventory"]),
            game=GameState.from_dict(d["game"]),
            battle=BattleState.from_dict(d["battle"]),
            agent_messages=[AgentMessage.from_dict(x) for x in d.get("agent_messages", [])],
        )
        # アクセスあったらTTLを延長（セッション継続のため）
        r.expire(rkey("session", session_id), SESSION_TTL_SECONDS)
        return bundle

    @staticmethod
    def new_session(session_id: str, player_name: str, job: str, chaos: int, rng: Optional[random.Random] = None) -> "SessionBundle":
        '''新規セッション（キャラ・インベントリ等まとめ）を作成して返す'''
        rng = rng or random.Random()
        character = Character.create_new(session_id, player_name, job, chaos, rng)
        inventory = Inventory()
        game = GameState(scenario_id=None, last_event="start", game_over=False)
        return SessionBundle(session_id=session_id, character=character, inventory=inventory, game=game)

    def append_agent_message(self, agent: str, role: str, content: str) -> None:
        '''エージェントメッセージを末尾に追加（保存は呼び出し側で）'''
        self.agent_messages.append(AgentMessage(agent=agent, role=role, content=content))
        # 多すぎるとつらいので適度に間引く
        if len(self.agent_messages) > 200:
            self.agent_messages = self.agent_messages[-100:]

    # --------- ゲーム内操作のヘルパ ---------

    def apply_moderation_penalty(self, reason: str, hp_loss: int = 1) -> int:
        '''モデレーション的に危険な発話があった際の「天罰」を適用する（減少HPを返す）'''
        # ブラックジョーク：やりすぎんなよ…という軽い抑止
        loss = self.character.take_damage(max(1, int(hp_loss)))
        self.battle.logs.append(self._fmt_system_log(f"天罰イベント発動（{reason}）：HP -{loss}"))
        return loss

    def give_item(self, item: Item) -> bool:
        '''プレイヤーにアイテムを付与する（成功可否）'''
        ok = self.inventory.add(item)
        if ok:
            self.battle.logs.append(self._fmt_system_log(f"アイテム獲得：{item.name}"))
        else:
            self.battle.logs.append(self._fmt_system_log("インベントリがいっぱいで拾えなかった…"))
        return ok

    def consume_item(self, item_id: str) -> Optional[str]:
        '''回復アイテムを消費し、効果を適用する（成功時はメッセージを返す）'''
        it = self.inventory.remove_by_id(item_id)
        if not it:
            return None
        if it.type != ItemType.CONSUMABLE:
            # 消耗品以外は消費不可（武器食うな）
            self.inventory.items.append(it)  # 戻しておく
            return None
        healed = self.character.heal(max(0, it.value))
        msg = f"{it.name} を使用し HP を {healed} 回復"
        self.battle.logs.append(self._fmt_system_log(msg))
        return msg

    def equip_weapon(self, item_id: str) -> Optional[str]:
        '''武器を装備して攻撃力に反映する（超簡易仕様）'''
        it = self.inventory.remove_by_id(item_id)
        if not it or it.type != ItemType.WEAPON:
            if it:  # 種別が違えば戻す
                self.inventory.items.append(it)
            return None
        self.character.atk += max(0, it.value)
        msg = f"武器 {it.name} を装備し ATK +{it.value}"
        self.battle.logs.append(self._fmt_system_log(msg))
        return msg

    def equip_armor(self, item_id: str) -> Optional[str]:
        '''防具を装備して防御力に反映する（超簡易仕様）'''
        it = self.inventory.remove_by_id(item_id)
        if not it or it.type != ItemType.ARMOR:
            if it:
                self.inventory.items.append(it)
            return None
        self.character.df += max(0, it.value)
        msg = f"防具 {it.name} を装備し DEF +{it.value}"
        self.battle.logs.append(self._fmt_system_log(msg))
        return msg

    def start_battle(self, enemy: Enemy) -> None:
        '''新規バトルを開始する（敵を設定しログを初期化）'''
        self.battle = BattleState(enemy=enemy, turn=0, logs=[])
        self.battle.logs.append(self._fmt_system_log(f"エンカウント！ {enemy.name} が現れた"))

    def next_turn(self) -> None:
        '''ターンを1進める'''
        self.battle.turn += 1

    def is_battle_over(self) -> bool:
        '''バトルが終了しているか（敵撃破 or プレイヤー死亡）を返す'''
        if not self.battle.enemy:
            return True
        if self.battle.enemy.hp <= 0:
            return True
        if self.character.is_dead():
            return True
        return False

    def _fmt_system_log(self, text: str) -> str:
        '''システムメッセージの整形'''
        ts = time.strftime("%H:%M:%S", time.localtime())
        return f"[{ts}] [SYS] {text}"


# =========================
# 便利関数（Flaskハンドラから使う想定）
# =========================

def load_or_create_session(session_id: str, player_name: str = "名無し", job: str = "旅人", chaos: int = 0) -> SessionBundle:
    '''セッションIDに対応するセッションを読み込む。無ければ新規作成する'''
    r = get_redis()
    bundle = SessionBundle.redis_load(session_id, r)
    if bundle:
        return bundle
    bundle = SessionBundle.new_session(session_id, player_name, job, chaos)
    bundle.redis_save(r)
    return bundle


def delete_session(session_id: str) -> bool:
    '''セッションを完全削除する（スライムLv1に戻す儀式）'''
    r = get_redis()
    n = r.delete(rkey("session", session_id))
    return n > 0


def battle_round(bundle: SessionBundle, player_action: str = "attack", rng: Optional[random.Random] = None) -> Dict[str, Any]:
    '''1ターン分のバトル進行を行い、結果のサマリを返す（超簡易）'''
    rng = rng or random.Random()
    if not bundle.battle.enemy:
        return {"error": "no_enemy"}

    # プレイヤー行動（現状は攻撃のみ）
    if player_action == "attack":
        bundle.battle.logs.append(bundle._fmt_system_log("あなたのターン"))
        dmg_to_enemy = bundle.battle.attack_enemy(bundle.character, rng)
    else:
        dmg_to_enemy = 0

    # 敵が生きていれば反撃
    dmg_to_player = 0
    if bundle.battle.enemy and bundle.battle.enemy.hp > 0:
        bundle.battle.logs.append(bundle._fmt_system_log("敵のターン"))
        dmg_to_player = bundle.battle.attack_player(bundle.character, rng)

    # ターン経過
    bundle.next_turn()

    # 終了判定
    over = bundle.is_battle_over()
    if over:
        if bundle.character.is_dead():
            bundle.game.game_over = True
            bundle.battle.logs.append(bundle._fmt_system_log("あなたは死亡した…（ゲームオーバー）"))
        else:
            bundle.battle.logs.append(bundle._fmt_system_log(f"{bundle.battle.enemy.name} を倒した！"))
    return {
        "turn": bundle.battle.turn,
        "enemy_hp": bundle.battle.enemy.hp if bundle.battle.enemy else 0,
        "player_hp": bundle.character.hp,
        "dmg_to_enemy": dmg_to_enemy,
        "dmg_to_player": dmg_to_player,
        "over": over,
    }


# =========================
# サンプル生成ヘルパ（テスト用）
# =========================

def sample_enemy() -> Enemy:
    '''テスト用の適当な敵データを返す'''
    # そのうちGPTに丸投げしても良い
    return Enemy(name="ゴブリン", hp=12, atk=8, df=4, description="そこらへんに湧く雑魚。だが油断は禁物。")


def sample_consumable() -> Item:
    '''テスト用の回復アイテム（ポーション）'''
    return Item(id="potion01", name="回復ポーション", type=ItemType.CONSUMABLE, value=5, description="HPをちょっと回復する。")


def sample_weapon() -> Item:
    '''テスト用の武器'''
    return Item(id="sword01", name="さびた剣", type=ItemType.WEAPON, value=2, description="一応切れる。たぶん。")


def sample_armor() -> Item:
    '''テスト用の防具'''
    return Item(id="cloth01", name="ぼろ布の服", type=ItemType.ARMOR, value=1, description="気休め程度の防御。")