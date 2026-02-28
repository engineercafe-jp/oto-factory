# Repository Guidelines

## Project Structure & Module Organization

The repository has three main areas:

### oto-factory バックエンド（`backend/`）

FastAPI バックエンド。テキストプロンプトを受け取り、ACE-Step 1.5 で MP3 を生成して返す。

- `backend/main.py`: FastAPI アプリ、lifespan（モデル初期化）、ワーカー
- `backend/config.py`: 環境変数設定（`OTO_` プレフィックス）
- `backend/models/schemas.py`: Pydantic モデル
- `backend/routers/generate.py`: API エンドポイント定義
- `backend/services/job_store.py`: インメモリジョブストア
- `backend/services/music_generator.py`: ACE-Step 呼び出しラッパー

### oto-factory フロントエンド（`frontend/`）

Next.js フロントエンド。バックエンドの API を呼び出してブラウザ UI を提供する。

- `frontend/app/`: App Router ページ
- `frontend/components/`: UI コンポーネント
- `frontend/hooks/`: カスタムフック（ジョブ管理、音声再生）
- `frontend/lib/`: API クライアント、型定義、ユーティリティ

### ACE-Step 1.5（`ACE-Step-1.5/`）

音楽生成エンジン本体。通常は変更しない。

- `ACE-Step-1.5/acestep/`: コアパッケージ（推論、UI、学習）
- `ACE-Step-1.5/docs/`: 多言語ドキュメント
- `ACE-Step-1.5/examples/`: 生成モードの JSON サンプル

## Build, Test, and Development Commands
Use `uv` for environment and runtime management.

### oto-factory バックエンド
- `cd /content/oto-factory && uv sync`: 依存関係インストール（ACE-Step 含む）
- `uv run oto-backend`: バックエンド起動（`0.0.0.0:8000`）
- `curl http://localhost:8000/api/health`: ヘルスチェック

### フロントエンド
- `cd frontend && npm install`: 依存関係インストール
- `npm run dev`: 開発サーバー起動（`localhost:3000`）
- `npm run lint`: ESLint 実行
- `npm run build`: production build 検証
- `.env.local` に `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` を設定する

### ACE-Step 1.5
- `cd ACE-Step-1.5 && uv sync`: 依存関係インストール
- `cd ACE-Step-1.5 && uv run acestep`: Gradio UI 起動（`127.0.0.1:7860`）
- `cd ACE-Step-1.5 && uv run acestep-api`: REST API サーバー起動
- `cd ACE-Step-1.5 && python -m unittest discover -s tests -p "test_*.py"`: root テスト実行
- `cd ACE-Step-1.5 && python -m unittest discover -s acestep -p "*_test.py"`: モジュールテスト実行
- `cd ACE-Step-1.5 && ./quick_test.sh`: 環境チェック（Linux/macOS）

## Coding Style & Naming Conventions
Follow `.editorconfig`: UTF-8, LF, final newline, trimmed trailing whitespace (Windows script files use CRLF). Python uses 4-space indentation and clear, small functions. Use `snake_case` for variables/functions/files and `PascalCase` for classes. Test files should be named `test_*.py` or `*_test.py`.

## Testing Guidelines
The project primarily uses `unittest`. For each behavior change, include at least one success-path test and one regression/edge-case test. Isolate GPU, filesystem, and external service dependencies with `unittest.mock` to keep tests deterministic and fast. Before opening a PR, run focused tests for changed modules.

## Commit & Pull Request Guidelines
Recent history favors Conventional Commit prefixes (`fix:`, `feat:`) and topic branches like `fix/...` or `feat/...`. Keep each PR scoped to one issue and avoid unrelated refactors. In the PR description, include:

- summary of the change
- explicit out-of-scope items
- non-target platform impact (CPU/CUDA/MPS/XPU)
- validation commands and results

## Security & Configuration Tips
Never commit secrets or local credentials. When adding configuration, update template files such as `.env.example` and `proxy_config.txt.example`, and inject real values through local environment variables.

When changing frontend behavior, update the user-facing markdown docs in the repository root as needed, especially `README.md`, `README_FRONTEND.md`, `install.md`, and SSH access guides.
