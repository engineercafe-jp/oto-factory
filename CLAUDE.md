# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

oto-factory は、音楽生成モデル ACE-Step 1.5 を使用して作業音をリアルタイム生成するアプリケーションである。

FastAPI バックエンドがテキストプロンプトを受け取り、ACE-Step 1.5 で MP3 を生成して返す。Next.js フロントエンドがブラウザ UI を提供する。

## 言語とスタイルのガイドライン

- **回答とドキュメント**: 日本語の常体（である調）を使用すること
- **コメントとログ**: 実装には多めのコメント、docstring、ログを追加し、内容を追いやすく配慮すること
- **参照実装**: `./ACE-Step-1.5` を参考にして実装すること

## 開発環境

### 必須要件

- Python 3.11（安定版のみ、プレリリース版は不可）
- パッケージマネージャ: `uv`
- GPU: CUDA 推奨、MPS/ROCm/Intel XPU/CPU もサポート
- Node.js（フロントエンド開発時）

### oto-factory バックエンドのセットアップ

```bash
# サブモジュールの初期化・更新（初回のみ）
git submodule update --init --recursive

# oto-factory ルートで依存関係をインストール
# ace-step も path dependency として一括解決される
cd /content/oto-factory
uv sync
```

### ACE-Step 1.5 単独のセットアップ（Gradio UI を使う場合）

```bash
cd ACE-Step-1.5
uv sync
```

## よく使うコマンド

### oto-factory バックエンドの操作

```bash
# バックエンド起動（推奨）
cd /content/oto-factory
uv run oto-backend

# または uvicorn で直接起動
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000

# ヘルスチェック
curl http://localhost:8000/api/health

# Swagger UI でAPI仕様を確認
# http://localhost:8000/docs
```

### フロントエンドの操作

```bash
cd /content/oto-factory/frontend

# 依存関係インストール（初回のみ）
npm install

# 開発サーバー起動
npm run dev

# Lint
npm run lint

# ビルド
npm run build
```

`.env.local` には以下を設定する。

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### ACE-Step 1.5 の起動（Gradio UI）

```bash
cd ACE-Step-1.5

# Gradio UI の起動 (http://localhost:7860)
uv run acestep

# REST API サーバーの起動 (http://localhost:8001)
uv run acestep-api

# モデルのダウンロード（初回起動時は自動）
uv run acestep-download
```

### 開発用コマンド

```bash
# バックエンドの import チェック
cd /content/oto-factory
uv run python -c "from backend.main import app; print('OK')"

# ACE-Step のテスト実行
cd ACE-Step-1.5
uv run python -m unittest discover -s acestep -p "*_test.py"
```

## アーキテクチャ

### oto-factory の構造

```
oto-factory/
├── ACE-Step-1.5/              # 音楽生成エンジン（サブモジュール）
├── backend/                   # FastAPI バックエンド
│   ├── main.py                # アプリエントリポイント、lifespan、ワーカー
│   ├── config.py              # 環境変数設定（OTO_ プレフィックス）
│   ├── models/
│   │   └── schemas.py         # Pydantic モデル（JobStatus、リクエスト/レスポンス）
│   ├── routers/
│   │   └── generate.py        # API エンドポイント（/api/generate 等）
│   └── services/
│       ├── job_store.py       # インメモリジョブストア（スレッドセーフ）
│       └── music_generator.py # ACE-Step 呼び出しラッパー（遅延 import）
├── frontend/                  # Next.js フロントエンド（App Router）
│   ├── app/                   # ページ
│   ├── components/            # UI コンポーネント
│   ├── hooks/                 # カスタムフック（ジョブ管理、音声再生）
│   └── lib/                   # API クライアント、型定義
├── pyproject.toml             # oto-factory プロジェクト設定
└── uv.lock                    # 依存関係ロックファイル
```

### バックエンドの処理フロー

```
POST /api/generate
  → JobStore.create() でジョブ登録（QUEUED）
  → asyncio.Queue に job_id を投入
  → 202 Accepted を即時返却

_queue_worker（バックグラウンド）
  → キューから job_id を取得
  → JobStore で RUNNING に更新
  → ThreadPoolExecutor で generate_and_save() を実行
  → 完了: JobStore.complete() / 失敗: JobStore.fail()

GET /api/jobs/{job_id}    → ジョブ状態・進捗を返す
GET /api/jobs/{job_id}/audio  → 完了済み MP3 を返す
```

### ACE-Step 1.5 の主要コンポーネント

1. **LM (Language Model)**: テキストプロンプトをメタデータに変換
   - モデルサイズ: 0.6B / 1.7B / 4B（VRAM に応じて選択）
   - バックエンド: `vllm` または `pt`

2. **DiT (Diffusion Transformer)**: 音声波形の生成
   - モデル: `acestep-v15-base`, `acestep-v15-sft`, `acestep-v15-turbo`

3. **VAE**: 音声のエンコード/デコード

### 重要な実装メモ

- `acestep` の import は `music_generator.py` で**遅延 import** とする（起動時エラー回避）
- `pyproject.toml` で `ace-step` を path dependency として定義し、`uv sync` で一括解決する
- ジョブキューは `asyncio.Queue`、音楽生成は `ThreadPoolExecutor(max_workers=1)` で逐次実行（OOM 防止）
- `get_checkpoints_dir()` でチェックポイントディレクトリを取得する（ACE-Step ルート自体は渡さない）
- フロントエンドは `status` 主導で画面遷移する。`stage` は表示専用である
- フロントエンドはアイドル時のみ `GET /api/health` を 30 秒間隔で行う
- 同一 `job_id` への `GET /api/jobs/{job_id}/audio` は 1 回だけ実行する

## 実装時の注意事項

### コーディング規約（AGENTS.md より）

1. **スコープの制限**
   - 1つのタスク/PR で1つの問題を解決する
   - 最小限の編集に留める: タスクに必要なファイル/関数のみ変更

2. **モジュール分解ポリシー**
   - 単一責任原則に従う
   - 目標モジュールサイズ: ≤150 LOC（推奨）、≤200 LOC（上限）

3. **テスト要件**
   - すべての動作変更とバグ修正にテストを追加/更新
   - テストファイル名: `*_test.py` または `test_*.py`
   - `unittest` スタイルを使用

4. **Python ベストプラクティス**
   - 新規/変更したモジュール、クラス、関数に docstring を必須で追加
   - 実用的な範囲で型ヒントを追加
   - エラーを明示的に処理（bare `except` を避ける）

## トラブルシューティング

### `acestep` が import できない

```bash
# uv sync が完了しているか確認
cd /content/oto-factory
uv sync

# サブモジュールが初期化されているか確認
git submodule update --init --recursive
```

### VRAM が不足する場合

1. より小さい LM モデルを選択（環境変数 `OTO_LM_MODEL=acestep-5Hz-lm-1.7B`）
2. LM を無効化（`OTO_LM_MODEL=""` で DiT のみモード）

### モデルのダウンロードに失敗する場合

```bash
cd ACE-Step-1.5
uv run acestep-download
```

## リファレンス

- [バックエンド設計書](./README_DESIGN.md)
- [フロントエンド設計・実装ガイド](./README_FRONTEND.md)
- [ACE-Step 1.5 README](./ACE-Step-1.5/README.md)
- [日本語インストールガイド](./ACE-Step-1.5/docs/ja/INSTALL.md)
- [推論ガイド（日本語）](./ACE-Step-1.5/docs/ja/INFERENCE.md)
- [エージェント向けガイド](./ACE-Step-1.5/AGENTS.md)
