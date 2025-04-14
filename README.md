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

    subgraph "AI GM システム (オーケストレーションフレームワーク)"
        Orch(オーケストレーター /<br>メインコントローラー)

        subgraph "専門エージェント群"
            Scenario(シナリオ / プロット管理)
            World(世界観 / 描写)
            NPC(NPC対話 / 行動)
            Rules(ルール裁定 / 判定)
            State(状態管理)
            Consistency[(整合性 / 矛盾チェック)] -.-> Orch %% Optional Agent
        end
    end

    %% プレイヤーからの入力
    P -- 1. アクション入力 (例: 罠を調べる) --> Orch;

    %% オーケストレーターによる指示
    Orch -- 2. 指示/解釈 --> Rules;
    Orch -- 7. 描写指示 --> World;
    Orch -- (必要に応じて) --> Scenario;
    Orch -- (必要に応じて) --> NPC;

    %% ルール裁定プロセス
    Rules -- 3. 判定に必要な情報要求 --> State;
    State -- 4. 要求された状態情報提供 (例: 探索技能値) --> Rules;
    Rules -- 5. 判定実行 (難易度設定/ダイスロール) --> Rules;
    Rules -- 6. 判定結果報告 (例: 失敗) --> Orch;

    %% 描写プロセス
    World -- 8. 生成された描写テキスト --> Orch;

    %% オーケストレーターからプレイヤーへの返答
    Orch -- 9. 最終的な応答生成 --> P;

    %% 状態更新 (例: 時間経過、判定結果など)
    Orch --> State;
    Rules --> State;
    Scenario --> State;
    NPC --> State;

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
