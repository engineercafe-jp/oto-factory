# 作業音リアルタイム生成アプリ 最小プロトタイプ設計（Python Only / vLLM専用）

## 1. 目的
ACE-Step 1.5 を使い、作業音を途切れにくく連続再生する最小プロトタイプを作る。  
初期段階では機能を絞り、**単一ユーザー・単一プロセス・vLLM固定**で成立させる。

## 2. スコープ
### 2.1 対象
- Pythonのみで構築（Webフロントは作らない）
- ACE-Step APIサーバー（`acestep-api`）を生成エンジンとして利用
- 20〜60秒セグメントを先読み生成して連続再生
- 小型LM（`acestep-5Hz-lm-0.6B`）固定

### 2.2 非対象（今はやらない）
- 複数ユーザー対応
- モデル自動切替
- 独自FastAPIラッパーの追加
- 認証、課金、管理画面

## 3. 結論（設計判断）
- **独自FastAPIでのラップは不要**。まずは `acestep-api` を直接利用する。
- 理由: ACE-Step側に非同期ジョブAPI（`/release_task`, `/query_result`）がすでにあるため。
- プロトタイプでは「生成制御」と「再生制御」を1つのPythonアプリで実装し、最短で価値検証する。

## 4. 構成
## 4.1 コンポーネント
1. **ACE-Step API Server**
- 起動コマンド: `uv run acestep-api`
- 役割: 音声生成ジョブ受付・実行・結果返却

2. **Prototype Controller（新規Pythonスクリプト）**
- 役割:
  - ジョブ投入（`/release_task`）
  - 状態ポーリング（`/query_result`）
  - 生成済み音声の再生キュー管理
  - キュー残量を見て次セグメントを先読み生成

3. **Audio Player**
- 最初は `ffplay` または `python-vlc` で十分
- 安定後にクロスフェードを追加

## 4.2 データフロー
1. Controller が最初の2〜3本を生成依頼
2. 生成完了した音声をローカルキューに格納
3. Player が先頭から再生
4. 残キューが閾値以下になったら次を生成
5. これをループし「連続再生体験」を作る

## 5. 実装仕様（Claude Code向け）
## 5.1 推奨ファイル構成
```text
prototype/
  config.py              # 定数・設定読込
  ace_client.py          # /release_task, /query_result クライアント
  generator_loop.py      # 先読み生成ロジック
  player.py              # 再生制御
  app.py                 # エントリポイント
```

## 5.2 最小設定値
- `LM_MODEL_PATH=acestep-5Hz-lm-0.6B`
- `LM_BACKEND=vllm`
- `SEGMENT_SECONDS=30`（初期値）
- `PREFETCH_TARGET=3`（キュー目標本数）
- `POLL_INTERVAL_SEC=1.5`
- `MAX_RETRY=2`

## 5.3 API利用方針
- 生成開始: `POST /release_task`
  - `task_type=text2music`
  - `thinking=true`
  - `lm_backend=vllm`
  - `lm_model_path=acestep-5Hz-lm-0.6B`
  - `audio_duration=30`（可変）
- 結果確認: `POST /query_result`
  - `status==1` を成功、`status==2` を失敗扱い
- 失敗時: 同条件でリトライ。連続失敗時は短いdurationへフォールバック。

## 6. 起動手順
1. ACE-Step APIサーバー起動
```bash
cd ACE-Step-1.5
uv run acestep-api --host 127.0.0.1 --port 8001
```

2. プロトタイプ実行
```bash
python prototype/app.py
```

## 7. 受け入れ条件（Definition of Done）
- 10分以上、再生停止なしで連続再生できる
- キュー残量が0になる前に次セグメントが補充される
- API一時失敗時に自動リトライして継続できる
- ログで「生成時間」「待機時間」「再生中キュー本数」を確認できる

## 8. 注意点
- **vLLM固定方針は主にNVIDIA/Linux向け**。Apple Siliconでは通常MLXが主流である。
- ただし本設計は「まずvLLMで動く最小PoCを作る」ことを優先する。
- mac対応は次フェーズでバックエンド切替（vLLM/MLX）を検討する。

## 9. 次フェーズ（今は実装しない）
- クロスフェードの高品質化
- 永続キュー（Redis等）
- 独自APIラッパー追加
- 複数ユーザー対応
