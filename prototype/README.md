# 作業音リアルタイム生成プロトタイプ

ACE-Step 1.5 を使用して、作業音を途切れなく連続再生する最小プロトタイプである。

## ステータス

✅ **動作確認済み** (2026-02-14)

- API クライアント実装完了
- セグメント生成テスト成功（3〜5秒/セグメント）
- キューイング機能動作確認済み
- 詳細は [`CHANGELOG.md`](./CHANGELOG.md) を参照

## 概要

- **目的**: 20〜60秒のセグメントを先読み生成し、連続再生する
- **対象**: Python のみ、単一ユーザー、vLLM 固定
- **構成**: ACE-Step API サーバー + Python 制御スクリプト

## ファイル構成

```
prototype/
├── README.md              # 本ファイル
├── config.py              # 定数・設定読込
├── ace_client.py          # /release_task, /query_result クライアント
├── generator_loop.py      # 先読み生成ロジック
├── player.py              # 再生制御
├── app.py                 # エントリポイント
└── generated_audio/       # 生成された音声ファイル（自動作成）
```

## 前提条件

- Google Colab A100 環境
- ACE-Step 1.5 がセットアップ済み
- `ffmpeg` がインストール済み（音声再生に必要）

## セットアップ

### 1. ffmpeg のインストール確認

```bash
# ffplay が利用可能か確認
which ffplay

# インストールされていない場合
sudo apt update && sudo apt install -y ffmpeg
```

### 2. ACE-Step API サーバーの起動

別のターミナル（または Colab セル）で ACE-Step API サーバーを起動：

```bash
cd /content/oto-factory/ACE-Step-1.5
uv run acestep-api --host 127.0.0.1 --port 8001
```

**注意**: API サーバーが起動するまで待機すること（初回は数分かかる場合あり）。

## テスト

プロトタイプを実行する前に、以下のテストスクリプトで動作確認できる。

### API 接続テスト

```bash
cd /content/oto-factory/prototype
python test_api.py
```

**確認内容**:
- ✅ `/health` エンドポイント
- ✅ `/release_task` エンドポイント
- ✅ `/query_result` エンドポイント

### 単一セグメント生成テスト

```bash
python test_single_segment.py
```

**期待結果**:
- タスク投入成功
- 約3〜5秒で生成完了
- 音声ファイル保存（157 KB）

### プロトタイプ動作確認

```bash
python test_prototype.py
```

**期待結果**:
- 2セグメント生成（各10秒）
- キューイング成功
- セグメント取得成功

## 実行方法

### 基本実行

```bash
cd /content/oto-factory/prototype
python app.py
```

### 環境変数でカスタマイズ

```bash
# セグメント長を60秒に設定
export SEGMENT_SECONDS=60

# 先読み本数を5本に設定
export PREFETCH_TARGET=5

# プロンプトをカスタマイズ
export DEFAULT_PROMPT="静かな雨音、リラックス、自然音"

# 実行
python app.py
```

## 設定項目

環境変数で以下をカスタマイズ可能：

| 環境変数 | デフォルト値 | 説明 |
|---------|-------------|------|
| `ACESTEP_API_HOST` | `127.0.0.1` | API サーバーのホスト |
| `ACESTEP_API_PORT` | `8001` | API サーバーのポート |
| `LM_MODEL_PATH` | `acestep-5Hz-lm-0.6B` | LM モデルパス |
| `LM_BACKEND` | `vllm` | LM バックエンド |
| `SEGMENT_SECONDS` | `30` | 1セグメントの秒数 |
| `PREFETCH_TARGET` | `3` | キュー目標本数 |
| `POLL_INTERVAL_SEC` | `1.5` | 結果確認間隔（秒） |
| `MAX_RETRY` | `2` | 最大リトライ回数 |
| `DEFAULT_PROMPT` | （環境音プロンプト） | 生成プロンプト |
| `LOG_LEVEL` | `INFO` | ログレベル |

## 動作説明

### フロー

1. **起動**: `app.py` を実行
2. **生成ループ開始**: `generator_loop.py` がバックグラウンドで動作
3. **初期セグメント生成**: 最初の3本（`PREFETCH_TARGET`）を生成
4. **再生開始**: キューから取り出して順次再生
5. **先読み継続**: キューが減ったら自動的に次を生成
6. **連続再生**: 上記を繰り返し、途切れなく再生

### ログ出力例

```
2026-02-14 09:00:00 [INFO] __main__: 作業音リアルタイム生成プロトタイプ
2026-02-14 09:00:00 [INFO] __main__: API URL: http://127.0.0.1:8001
2026-02-14 09:00:00 [INFO] __main__: プロンプト: 穏やかな環境音、集中作業に適した雰囲気
2026-02-14 09:00:00 [INFO] __main__: セグメント長: 30秒
2026-02-14 09:00:00 [INFO] __main__: 先読み目標: 3本
2026-02-14 09:00:05 [INFO] generator_loop: セグメント#1 生成開始
2026-02-14 09:00:15 [INFO] generator_loop: セグメント#1 生成完了: segment_0001.wav (10.2秒)
2026-02-14 09:00:15 [INFO] __main__: [1] 再生: segment_0001.wav | キュー残: 2 | 経過時間: 15秒
```

## トラブルシューティング

### 1. API サーバーに接続できない

**エラー**: `タスク投入失敗: Connection refused`

**解決策**:
- ACE-Step API サーバーが起動しているか確認
- ポート番号が正しいか確認（デフォルト: 8001）

```bash
# API サーバーが起動しているか確認
curl http://127.0.0.1:8001/health || echo "API サーバーが起動していません"
```

### 2. ffplay が見つからない

**エラー**: `ffplay が見つかりません`

**解決策**:
```bash
sudo apt update && sudo apt install -y ffmpeg
```

### 3. セグメント生成が遅い

**現象**: キューが空になり、待機時間が長い

**解決策**:
- セグメント長を短くする: `export SEGMENT_SECONDS=20`
- 先読み本数を増やす: `export PREFETCH_TARGET=5`
- より高速なモデルに変更（ただし品質が下がる）

### 4. 音声が再生されない

**解決策**:
- 生成された音声ファイルを手動で確認:
  ```bash
  ls -lh /content/oto-factory/prototype/generated_audio/
  ffplay /content/oto-factory/prototype/generated_audio/segment_0001.wav
  ```

## 受け入れ条件（Definition of Done）

- ✅ 10分以上、再生停止なしで連続再生できる
- ✅ キュー残量が0になる前に次セグメントが補充される
- ✅ API一時失敗時に自動リトライして継続できる
- ✅ ログで「生成時間」「待機時間」「再生中キュー本数」を確認できる

## 次フェーズ（今は実装しない）

- クロスフェードの高品質化
- 永続キュー（Redis等）
- 独自APIラッパー追加
- 複数ユーザー対応
- Web UI

## ライセンス

本プロトタイプは oto-factory プロジェクトの一部であり、同じライセンスが適用される。
