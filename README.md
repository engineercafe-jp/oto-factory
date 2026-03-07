# oto-factory

## 概要

このプロジェクトは音楽生成モデル [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) を使用して、作業音をリアルタイム生成するアプリケーションを提供する。

テキストプロンプトを入力するだけで MP3 楽曲を生成し、ブラウザ上で再生・ダウンロードできる。

現在の UI は `frontend/` の Next.js App Router 実装であり、1 画面で以下を行う。

- プロンプト送信
- ジョブ進捗のポーリング表示
- 完了後の MP3 取得
- 自動再生の試行と手動再生フォールバック
- MP3 ダウンロード

## システム構成

```
ブラウザ (Next.js フロントエンド)
    ↕ HTTP (port 3000)
FastAPI バックエンド (port 8000)
    ↕ Python API
ACE-Step 1.5 (音楽生成エンジン)
    ↕
GPU (CUDA / MPS / CPU)
```

## クイックスタート

### 前提条件

- Python 3.11
- `uv`（パッケージマネージャ）
- CUDA GPU 推奨（T4 以上）
- Node.js（フロントエンドを動かす場合）

### バックエンド起動

```bash
cd /content/oto-factory

# 1. サブモジュールの初期化（初回のみ）
git submodule update --init --recursive

# 2. 依存関係インストール（ACE-Step 含む全依存を一括解決）
uv sync

# 3. バックエンド起動
uv run oto-backend
# または
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

起動後、`http://localhost:8000/docs` で Swagger UI にアクセスできる。

モデルの初期読み込みには数分かかる。`GET /api/health` で `"model_loaded": true` になれば準備完了である。

### フロントエンド起動

```bash
cd /content/oto-factory/frontend

# 依存関係インストール（初回のみ）
npm install

# 開発サーバー起動
npm run dev

# 品質確認
npm run lint
npm run build
```

起動後、`http://localhost:3000` でフロントエンドにアクセスできる。

バックエンドのエンドポイントは `.env.example` を参考に `.env.local` で設定する。

```bash
cp .env.example .env.local
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### フロントエンドの使い方

1. `http://localhost:3000` を開く
2. ヘルス表示で backend が `online` になっていることを確認する
3. プロンプトを入力し、長さを選択する
4. 必要なら「詳細設定」で `BPM` と `Seed` を指定する
5. `生成を開始する` を押す
6. 進捗カードで `queued` / `running` / `downloading` / `completed` を確認する
7. 完了後、再生カードで音声を確認し、必要ならダウンロードする

### フロントエンドの現在の挙動

- `GET /api/health` は初回表示時に実行し、アイドル時は 30 秒間隔で再取得する
- ジョブ状態は表示中 2 秒、非表示時 5 秒で `GET /api/jobs/{job_id}` をポーリングする
- `completed` 後の `GET /api/jobs/{job_id}/audio` は同一 `job_id` に対して 1 回だけ実行する
- 音声取得後は `play()` で自動再生を試み、失敗した場合は手動再生ボタンを出す
- 1 ジョブ進行中は再送を禁止する

### ACE-Step Gradio UI（直接使用する場合）

```bash
cd /content/oto-factory/ACE-Step-1.5
uv sync
uv run acestep --language ja --server-name 0.0.0.0
```

詳細は [`install.md`](./install.md) を参照のこと。

## プロジェクト構成

```
oto-factory/
├── ACE-Step-1.5/               # ACE-Step 1.5 サブモジュール（音楽生成エンジン）
├── backend/                    # FastAPI バックエンド
│   ├── main.py                 # アプリケーションエントリポイント、lifespan
│   ├── config.py               # 環境変数設定（OTO_ プレフィックス）
│   ├── models/
│   │   └── schemas.py          # Pydantic リクエスト/レスポンスモデル
│   ├── routers/
│   │   └── generate.py         # API エンドポイント定義
│   └── services/
│       ├── job_store.py        # インメモリジョブストア
│       └── music_generator.py  # ACE-Step 呼び出しラッパー
├── frontend/                   # Next.js フロントエンド
│   ├── app/                    # App Router
│   ├── components/             # UI コンポーネント
│   ├── hooks/                  # カスタムフック
│   └── lib/                    # API クライアント・型定義
├── pyproject.toml              # oto-factory プロジェクト設定
├── uv.lock                     # 依存関係ロックファイル
├── README.md                   # 本ファイル
├── README_DESIGN.md            # バックエンド設計書
├── README_FRONTEND.md          # フロントエンド設計書
├── CLAUDE.md                   # Claude Code 向けガイド
├── AGENTS.md                   # エージェント向けガイドライン
├── install.md                  # Google Colab インストールガイド
├── mac-connection-guide.md     # MacBook Air 接続ガイド
└── ssh-forwarding-guide.md     # SSH ポートフォワーディング全ガイド
```

## API エンドポイント

| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/api/generate` | 音楽生成ジョブを投入（即時返却） |
| `GET` | `/api/jobs/{job_id}` | ジョブの状態・進捗を確認 |
| `GET` | `/api/jobs/{job_id}/audio` | 生成済み MP3 をダウンロード |
| `GET` | `/api/health` | サーバー・モデルの状態確認 |

詳細は [`README_DESIGN.md`](./README_DESIGN.md) または `http://localhost:8000/docs` を参照のこと。

## ローカルマシンからのアクセス

SSH ポートフォワーディングで Colab 上のサービスにアクセスできる。

```bash
# バックエンド API (port 8000) とフロントエンド (port 3000) を同時に転送
ssh -L 8000:localhost:8000 -L 3000:localhost:3000 colab
```

または、Gradio UI も含めて転送する場合：

```bash
ssh -L 7860:localhost:7860 -L 8000:localhost:8000 -L 3000:localhost:3000 colab
```

`~/.ssh/config` への永続設定は [`mac-connection-guide.md`](./mac-connection-guide.md) を参照のこと。

トンネル実行後のアクセス先は以下である。

- フロントエンド: `http://localhost:3000`
- バックエンド API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Gradio UI: `http://localhost:7860`

## 環境変数

バックエンドは以下の環境変数で設定可能である（プレフィックス `OTO_`）。

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `OTO_HOST` | `0.0.0.0` | バインドするホスト |
| `OTO_PORT` | `8000` | バインドするポート |
| `OTO_ACESTEP_ROOT` | `./ACE-Step-1.5` | ACE-Step ルートディレクトリ |
| `OTO_DIT_CONFIG` | `acestep-v15-turbo` | DiT モデル設定名 |
| `OTO_LM_MODEL` | `""` (自動選択) | LM モデル名 |
| `OTO_LM_BACKEND` | `vllm` | LM バックエンド |
| `OTO_DEVICE` | `auto` | デバイス（cuda/mps/cpu）|
| `OTO_AUDIO_DIR` | `./.cache/audio` | 生成音声の保存先 |
| `OTO_JOB_TTL` | `3600` | ジョブの有効期限（秒）|
| `OTO_QUEUE_MAX` | `100` | キューの最大サイズ |

## 利用可能モデルと設定方法

### DiT モデル（`OTO_DIT_CONFIG`）

このサービスのデフォルトは `acestep-v15-turbo`。

- `acestep-v15-turbo`（デフォルト）

### LM モデル（`OTO_LM_MODEL`）

`OTO_LM_MODEL` は空文字のとき GPU に応じて自動選択される。
ACE-Step 1.5 で選択可能な代表的な LM モデルは以下。

- `acestep-5Hz-lm-0.6B`
- `acestep-5Hz-lm-1.7B`
- `acestep-5Hz-lm-4B`

> 注: このリポジトリの初期チェックポイントには `acestep-5Hz-lm-1.7B` が含まれている。  
> 他サイズ（`0.6B` / `4B`）を使う場合は、ACE-Step 側のチェックポイント取得手順に従って追加すること。

### 設定例

環境変数を前置して起動すれば、CLI からそのままモデルを切り替えられる。

```bash
# 例1: LMを明示指定（1.7B）
OTO_LM_MODEL=acestep-5Hz-lm-1.7B uv run oto-backend

# 例2: DiTを明示指定（turbo）
OTO_DIT_CONFIG=acestep-v15-turbo uv run oto-backend

# 例3: LMを自動選択に戻す
OTO_LM_MODEL="" uv run oto-backend
```

## ドキュメント

### アプリケーション
- **[README_DESIGN.md](./README_DESIGN.md)**: バックエンド設計書（API 仕様、モジュール構成）
- **[README_FRONTEND.md](./README_FRONTEND.md)**: フロントエンド設計・実装・利用ガイド

### 環境構築
- **[install.md](./install.md)**: Google Colab での詳細なインストール手順（A100/T4 対応）
- **[mac-connection-guide.md](./mac-connection-guide.md)**: MacBook Air からの接続手順
- **[ssh-forwarding-guide.md](./ssh-forwarding-guide.md)**: すべてのアクセス方法の比較

### 開発ガイド
- **[CLAUDE.md](./CLAUDE.md)**: Claude Code 向けの開発ガイド
- **[AGENTS.md](./AGENTS.md)**: エージェント向けガイドライン

## 参考リンク

- [ACE-Step 1.5 公式リポジトリ](https://github.com/ace-step/ACE-Step-1.5)
- [ACE-Step 1.5 日本語ドキュメント](./ACE-Step-1.5/docs/ja/)
