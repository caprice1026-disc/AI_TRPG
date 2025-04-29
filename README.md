# AI_TRPG
OpenAIのエージェントフレームワークを使用したTRPG

# 現状
~~OpenAIのフレームワークであるSwarmの使用感を確認中。~~

→swarmではなく正式なエージェントフレームワークが発表されたのでそちらかlangchainに切り替える。

## エージェント

```mermaid
graph LR
    subgraph "プレイヤー空間"
        P[プレイヤー]
    end

    subgraph "AI GM システム"
        Orch(オーケストレーター)
        Scenario(シナリオ / プロット管理)
        World(世界観 / 描写)
        Rules(ルール設定 / 判定)
        State(状態管理)

        %% 状態管理への接続: 各エージェントは状態を随時参照・更新
        Orch -.-> State
        Scenario -.-> State
        World -.-> State
        Rules -.-> State
    end

    %% --- フロー定義 ---

    %% 1. プレイヤー入力 → オーケストレーター
    P -- 1 アクション入力 --> Orch

    %% 2. オーケストレーター → シナリオ、プロット管理
    %% (ダイスロール要否など検討)
    Orch -- 2 状況に応じた指示 --> Scenario

    %% 3. シナリオ、プロット管理からの分岐
    subgraph "3 状況に応じた処理分岐"
        direction LR
        %% 分岐ノード定義
        World_Proc(描写処理)
        Rules_Proc(判定処理)
        Combat_Proc(戦闘処理)
        World_Combat_Start(戦闘描写 開始)
        World_Combat_Cont(戦闘描写 継続/結果)

        %% シナリオからの分岐接続
        Scenario -- 3a. ダイスロール不要 --> World_Proc
        Scenario -- 3b. ダイスロール要 --> Rules_Proc
        Scenario -- 3c. 戦闘 --> Combat_Proc

        %% 各処理から担当エージェントへ接続
        World_Proc --> World
        Rules_Proc --> Rules

        %% 3b. ダイスロール要の場合: 判定後に描写
        Rules -- 判定結果 --> World

        %% 3c. 戦闘の場合: 戦闘描写 → 判定 → 戦闘描写 → 世界観描写
        Combat_Proc --> World_Combat_Start
        %% 戦闘判定指示
        World_Combat_Start --> Rules
        %% 戦闘判定結果を受けて描写継続/結果
        Rules -- 戦闘判定結果 --> World_Combat_Cont
        %% 戦闘結果を反映した世界観描写へ
        World_Combat_Cont --> World
    end

    %% 4. 世界観描写 → オーケストレーター → プレイヤー
    World -- 4a. 生成された描写 --> Orch
    Orch -- 4b. 最終的な応答生成 --> P

    %% 内部的な状態参照・更新 (点線で表現)
    Rules <--> State
    World <--> State
    Scenario <--> State

```


TRPGを実装するために、以下のエージェントを実装

1. **ゲームマスターエージェント（GMエージェント）**
   - プレイヤーの行動に応じてストーリーを進行し、シナリオを管理する。

2. **戦闘エージェント**
   - 戦闘の処理を担当し、ダメージ計算や結果の判定を行う。

3. **キャラクター管理エージェント**
   - キャラクターの作成、レベルアップ、ステータス更新を行う。

4. **アイテム管理エージェント**
   - アイテムの追加・削除やインベントリの管理を行う。

5. **ワールドエージェント**
   - ゲーム内の世界や環境、イベントを管理する。

6. **NPCエージェント**
   - 非プレイヤーキャラクターの行動や会話を制御する。

これらのエージェントを組み合わせて、TRPGのシステムを構築する予定。
