# oto-factory

## 概要

oto-factory は、音楽生成モデル [ACE-Step 1.5](https://github.com/ace-step/ACE-Step-1.5) を使って**作業用 BGM をその場で生成**するアプリケーションである。

テキストで雰囲気を伝えるだけで AI が MP3 楽曲を生成し、ブラウザ上で再生・ダウンロードできる。

### 主な機能

- **単発生成** — プロンプトを入力して 1 曲生成・再生・ダウンロード
- **ループ生成** — 再生中に次の曲を先行生成し、途切れなくシームレスに連続再生
- **リアルタイム進捗表示** — 生成状況をポーリングでリアルタイム表示
- **フォーム編集自由** — ループ中もプロンプトや設定を変更でき、次の生成から反映

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

### 使い方

#### 基本（1 曲ずつ生成する）

1. `http://localhost:3000` を開く
2. 画面上部のヘルス表示で server が **online** になっていることを確認する
3. プロンプト欄に作りたい曲の雰囲気を入力する（例: `Calm lofi beats with rain sounds, warm and cozy`）
4. 長さ（30 / 60 / 120 / 180 秒）を選択する
5. 必要に応じて「詳細設定」から BPM や Seed を指定する
6. **「生成する」** ボタンを押す
7. 進捗カードでステータスが `queued → running → completed` と遷移するのを確認する
8. 完了後、プレイヤーで自動再生される。「MP3 をダウンロード」で保存もできる

#### ループ生成（途切れなく連続再生する）

1. プロンプトと長さを設定する
2. **「ループ生成」** ボタンを押す
3. 第 1 トラックが生成され、自動再生が始まる
4. 再生中に次のトラックが自動的に先行生成される（プレイヤー下部に「次のトラック: 生成中...」→「準備完了」と表示）
5. 曲が終わると次のトラックがシームレスに再生される
6. **ループ中もフォームは編集可能** — プロンプトや BPM を変えると、次の生成から反映される
7. **「ループ停止」** を押すと、現在の曲が最後まで再生された後に停止する

> **ヒント:** 生成時間は GPU 性能と曲の長さによって 15〜90 秒程度で変動する。次のトラックの生成が曲の再生時間内に完了しない場合は「次のトラックを準備中です」と表示され、完了次第自動的に再生が再開される。

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
│   ├── app/                    # App Router（ページ、グローバル CSS）
│   ├── components/             # UI コンポーネント（フォーム、プレイヤー等）
│   ├── hooks/                  # カスタムフック（ジョブ管理、音声再生、ループ生成）
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
