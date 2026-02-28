# oto-factory バックエンド設計書

## 概要

ブラウザからテキストプロンプト（例：「シンプルなハウスミュージック」）を受信し、1分間の作業音を生成して MP3 として返す FastAPI バックエンドを設計する。音楽生成には ACE-Step 1.5 の推論パイプラインを使用する。

生成には数十秒〜数分を要するため、非同期ジョブキュー方式を採用し、ジョブ投入・状態確認・結果取得を分離する。

---

## アーキテクチャ

```
┌──────────┐       ┌────────────────────────────────────┐
│ ブラウザ  │       │         FastAPI バックエンド         │
│          │       │                                    │
│  POST ───┼──────▶│  /api/generate                     │
│  prompt  │       │    ↓ ジョブ登録                      │
│          │       │    ↓ asyncio.Queue に投入            │
│          │       │    ↓ job_id を即時返却               │
│          │       │                                    │
│  GET ────┼──────▶│  /api/jobs/{job_id}                │
│  ポーリング│       │    ↓ ジョブ状態を返却               │
│          │       │                                    │
│  GET ────┼──────▶│  /api/jobs/{job_id}/audio          │
│  ダウンロード│     │    ↓ MP3 ファイルを返却             │
│          │       │                                    │
│          │       │  ┌──────────────────────────────┐  │
│          │       │  │ バックグラウンドワーカー        │  │
│          │       │  │  Queue → generate_music()    │  │
│          │       │  │  → AudioSaver (MP3変換)      │  │
│          │       │  └──────────────────────────────┘  │
└──────────┘       └────────────────────────────────────┘
                              │
                              ▼
                   ┌────────────────────┐
                   │  ACE-Step 1.5      │
                   │  ├ LLM Handler     │
                   │  ├ DiT Handler     │
                   │  └ VAE             │
                   └────────────────────┘
```

---

## 実装前提（必読）

ジュニアエンジニアが迷いやすい箇所を先に固定する。

- **標準の実行方法は `uv sync` + `uv run` とする**。`sys.path` の追加は補助策であり、依存解決の主手段ではない。
- **依存パッケージ名と import 名は異なる**。`uv` / `pyproject.toml` 上の依存名は `ace-step`、Python の import 名は `acestep` である。
- **`stage` は表示用テキストであり API 契約ではない**。クライアントは `queued` / `running` / `completed` / `failed` の `status` のみを分岐条件に使い、`stage` はそのまま表示する。
- **LM のチェックポイントは `get_checkpoints_dir()` が返すディレクトリから解決する**。`ACE-Step-1.5` ルートそのものを `checkpoint_dir` として渡さない。
- **`backend/services/music_generator.py` では `acestep` の import を関数内で遅延させる**。これにより `main.py` の import 時点で `acestep` 未解決になりにくくなる。

---

## 使用ライブラリ・モジュール

### 外部ライブラリ（pip/uv でインストール）

| ライブラリ | バージョン | 用途 | インストール元 |
|-----------|-----------|------|--------------|
| `fastapi` | >=0.110.0 | Web フレームワーク | PyPI |
| `uvicorn[standard]` | >=0.27.0 | ASGI サーバー | PyPI |
| `pydantic` | >=2.0 | リクエスト/レスポンスのバリデーション | FastAPI の依存関係として自動インストール |
| `pydantic-settings` | >=2.0 | 環境変数からの設定読み込み | PyPI |
| `loguru` | >=0.7.3 | 構造化ログ | PyPI |

> **注意**: `torch`, `torchaudio`, `transformers`, `diffusers` 等の ML ライブラリは ACE-Step 1.5 サブモジュール側の依存関係に含まれている。バックエンド側で個別にインストールする必要はない。

### ACE-Step 1.5 内部モジュール（サブモジュールから利用）

以下のモジュールを `acestep` パッケージからインポートして使用する。標準運用では `uv sync` 後に `uv run ...` で実行する。`sys.path` への `ACE-Step-1.5` 追加は補助策として使うが、トップレベル import 依存を避けるため `music_generator.py` では遅延 import を採用する。

| モジュール | インポートパス | 用途 |
|-----------|-------------|------|
| 推論 API | `from acestep.inference import generate_music, GenerationParams, GenerationConfig, GenerationResult` | 音楽生成の統合 API |
| DiT ハンドラ | `from acestep.handler import AceStepHandler` | DiT モデルの初期化・推論 |
| LLM ハンドラ | `from acestep.llm_inference import LLMHandler` | 5Hz LM の初期化・推論 |
| GPU 設定 | `from acestep.gpu_config import get_gpu_config, set_global_gpu_config, get_gpu_memory_gb, GPUConfig` | GPU 自動検出と最適化設定 |
| モデルダウンロード | `from acestep.model_downloader import get_checkpoints_dir` | チェックポイントディレクトリの取得 |

### 標準ライブラリ

| モジュール | 用途 |
|-----------|------|
| `asyncio` | 非同期ジョブキュー（`asyncio.Queue`） |
| `threading` | ジョブストアのスレッドセーフなロック（`threading.Lock`） |
| `concurrent.futures` | ブロッキング処理のオフロード（`ThreadPoolExecutor`） |
| `uuid` | ジョブ ID 生成（`uuid.uuid4()`） |
| `datetime` | ジョブのタイムスタンプ管理 |
| `pathlib` | ファイルパスの操作 |
| `os` | 環境変数・ディレクトリ操作 |
| `sys` | `sys.path` への ACE-Step パス追加 |

---

## pyproject.toml

oto-factory ルートに `pyproject.toml` を新規作成する。ACE-Step 1.5 は path dependency として取り込み、`uv sync` で oto-factory と ACE-Step の依存をまとめて解決する。

```toml
[project]
name = "oto-factory"
version = "0.1.0"
description = "作業音リアルタイム生成バックエンド"
requires-python = "==3.11.*"
dependencies = [
    "ace-step",
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic-settings>=2.0",
    "loguru>=0.7.3",
]

[tool.uv.sources]
ace-step = { path = "./ACE-Step-1.5", editable = true }

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project.scripts]
oto-backend = "backend.main:cli_main"
```

> **ポイント**:
> - `uv` 上の依存名は `ace-step`、Python の import 名は `acestep` である。
> - `ace-step` を path dependency として登録することで、`uv sync` 時に ACE-Step 1.5 の依存関係も一緒に解決される。
> - `sys.path` 追加は補助策であり、基本は `uv run oto-backend` で起動する。

---

## エンドポイント設計

### 1. `POST /api/generate` — ジョブ投入

テキストプロンプトを受け取り、音楽生成ジョブを非同期で開始する。

**リクエスト:**

```json
{
  "prompt": "シンプルなハウスミュージック",
  "duration": 60,
  "bpm": null,
  "seed": null
}
```

| フィールド | 型 | デフォルト | 説明 |
|-----------|------|-----------|------|
| `prompt` | `str` | **必須** | 生成する音楽の説明文（512文字以内） |
| `duration` | `int` | `60` | 生成する音楽の長さ（秒）。10〜600 の範囲 |
| `bpm` | `int \| null` | `null` | テンポ（30〜300）。null の場合は LM が自動決定 |
| `seed` | `int \| null` | `null` | 乱数シード。null の場合はランダム |

**レスポンス（202 Accepted）:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "queued",
  "message": "ジョブを受け付けた"
}
```

**処理フロー:**

1. Pydantic によるリクエストバリデーション（prompt 必須、duration 範囲チェック等）
2. `uuid.uuid4()` でジョブ ID を生成
3. `JobStore.create()` でジョブを `queued` 状態で登録
4. `asyncio.Queue.put_nowait()` でジョブ ID をキューに投入（`QueueFull` 時はロールバックして 503）
5. `GenerateJobResponse` を 202 ステータスで即時返却

---

### 2. `GET /api/jobs/{job_id}` — ジョブ状態確認

ジョブの現在の状態と進捗を返す。クライアントはこのエンドポイントを 2 秒間隔でポーリングして完了を待つ。

**レスポンス（200 OK）:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 0.45,
  "stage": "Generating music (batch size: 1)...",
  "created_at": "2026-02-28T12:00:00Z",
  "completed_at": null,
  "error": null
}
```

| フィールド | 型 | 説明 |
|-----------|------|------|
| `job_id` | `str` | ジョブ ID |
| `status` | `str` | `queued` / `running` / `completed` / `failed` |
| `progress` | `float \| null` | 進捗率 0.0〜1.0。`queued` 時は null |
| `stage` | `str \| null` | 現在の処理段階の説明。表示用テキストであり、値の厳密一致には依存しない |
| `created_at` | `str` | ジョブ作成日時（ISO 8601） |
| `completed_at` | `str \| null` | ジョブ完了日時 |
| `error` | `str \| null` | エラーメッセージ（`failed` 時のみ） |

**ジョブが存在しない場合（404 Not Found）:**

```json
{
  "detail": "ジョブが見つからない"
}
```

---

### 3. `GET /api/jobs/{job_id}/audio` — 音声ダウンロード

生成完了した MP3 ファイルを返す。

**レスポンス（200 OK）:**

- `Content-Type: audio/mpeg`
- `Content-Disposition: attachment; filename="oto_{job_id}.mp3"`
- ボディ: MP3 バイナリ

**ジョブ未完了の場合（409 Conflict）:**

```json
{
  "detail": "ジョブがまだ完了していない（現在の状態: running）"
}
```

**ジョブが存在しない場合（404 Not Found）:**

```json
{
  "detail": "ジョブが見つからない"
}
```

---

### 4. `GET /api/health` — ヘルスチェック

サーバーとモデルの状態を返す。

**レスポンス（200 OK）:**

```json
{
  "status": "ok",
  "model_loaded": true,
  "gpu": "NVIDIA A100-SXM4-40GB",
  "vram_gb": 40.0,
  "queue_size": 2
}
```

---

## モジュール構成

```
oto-factory/
├── ACE-Step-1.5/              # サブモジュール（既存・変更不要）
├── backend/
│   ├── __init__.py            # 空ファイル
│   ├── main.py                # FastAPI アプリ生成、lifespan、ワーカー
│   ├── config.py              # Settings クラス（環境変数読み込み）
│   ├── routers/
│   │   ├── __init__.py        # 空ファイル
│   │   └── generate.py        # 全エンドポイントの定義
│   ├── services/
│   │   ├── __init__.py        # 空ファイル
│   │   ├── music_generator.py # ACE-Step 呼び出しラッパー
│   │   └── job_store.py       # ジョブ状態管理
│   └── models/
│       ├── __init__.py        # 空ファイル
│       └── schemas.py         # Pydantic モデル定義
├── pyproject.toml             # プロジェクト設定（新規作成）
└── README_DESIGN.md           # 本ファイル
```

以下、各ファイルの実装内容を詳細に記述する。

---

## ファイル別 実装仕様

### 1. `backend/models/schemas.py` — データモデル定義

**目的**: リクエスト・レスポンスの型を定義する。FastAPI はこれらの型を使ってバリデーションと OpenAPI ドキュメント生成を自動で行う。

**依存ライブラリ**:
- `pydantic`: `BaseModel`, `Field`
- `enum`: `Enum`
- `datetime`: `datetime`
- `typing`: `Optional`

```python
"""リクエスト・レスポンスの Pydantic モデル定義。"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# ジョブ状態の列挙型
# ---------------------------------------------------------------------------
class JobStatus(str, Enum):
    """ジョブのライフサイクル状態。"""

    QUEUED = "queued"        # キューに投入済み、処理待ち
    RUNNING = "running"      # 音楽生成中
    COMPLETED = "completed"  # 生成完了、MP3 ダウンロード可能
    FAILED = "failed"        # 生成失敗


# ---------------------------------------------------------------------------
# リクエストモデル
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    """POST /api/generate のリクエストボディ。"""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="生成する音楽の説明文",
        examples=["シンプルなハウスミュージック", "落ち着いたローファイヒップホップ"],
    )
    duration: int = Field(
        default=60,
        ge=10,
        le=600,
        description="生成する音楽の長さ（秒）。10〜600 の範囲",
    )
    bpm: Optional[int] = Field(
        default=None,
        ge=30,
        le=300,
        description="テンポ。null の場合は LM が自動決定",
    )
    seed: Optional[int] = Field(
        default=None,
        description="乱数シード。null の場合はランダム",
    )


# ---------------------------------------------------------------------------
# レスポンスモデル
# ---------------------------------------------------------------------------
class GenerateJobResponse(BaseModel):
    """POST /api/generate のレスポンス。"""

    job_id: str = Field(description="ジョブの一意識別子（UUID v4）")
    status: JobStatus = Field(description="ジョブの状態")
    message: str = Field(description="人間向けメッセージ")


class JobStatusResponse(BaseModel):
    """GET /api/jobs/{job_id} のレスポンス。"""

    job_id: str
    status: JobStatus
    progress: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="進捗率 0.0〜1.0",
    )
    stage: Optional[str] = Field(
        default=None,
        description="現在の処理段階（例: 'LM 推論中', 'DiT 推論中'）",
    )
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """GET /api/health のレスポンス。"""

    status: str
    model_loaded: bool
    gpu: str
    vram_gb: float
    queue_size: int
```

---

### 2. `backend/models/__init__.py`

```python
"""Pydantic モデルパッケージ。"""
```

---

### 3. `backend/config.py` — アプリケーション設定

**目的**: 環境変数から設定値を読み込む。`pydantic-settings` の `BaseSettings` を使用し、環境変数プレフィックス `OTO_` を付与する。

**依存ライブラリ**:
- `pydantic-settings`: `BaseSettings`, `SettingsConfigDict`
- `pathlib`: `Path`

```python
"""アプリケーション設定。環境変数から読み込む。"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    環境変数から設定を読み込む。

    プレフィックス OTO_ を使用する。
    例: OTO_PORT=8000 → self.port = 8000
    """

    # サーバー設定
    host: str = "0.0.0.0"
    port: int = 8000

    # ACE-Step 1.5 設定
    acestep_root: str = "./ACE-Step-1.5"
    dit_config: str = "acestep-v15-turbo"
    lm_model: str = ""           # 空文字の場合は GPU に応じて自動選択
    lm_backend: str = "vllm"     # "vllm" または "pt"
    device: str = "auto"         # "auto", "cuda", "mps", "cpu"

    # 生成した音声の保存先
    audio_output_dir: str = Field(
        default="./.cache/audio",
        validation_alias="OTO_AUDIO_DIR",
    )

    # ジョブ管理
    job_ttl_seconds: int = Field(
        default=3600,
        validation_alias="OTO_JOB_TTL",
    )
    queue_max_size: int = Field(
        default=100,
        validation_alias="OTO_QUEUE_MAX",
    )

    model_config = SettingsConfigDict(env_prefix="OTO_")

    @property
    def acestep_root_path(self) -> Path:
        """ACE-Step ルートの Path オブジェクトを返す。"""
        return Path(self.acestep_root).resolve()

    @property
    def audio_output_path(self) -> Path:
        """音声出力ディレクトリの Path オブジェクトを返す。"""
        return Path(self.audio_output_dir).resolve()


# シングルトンインスタンス。各モジュールからインポートして使用する。
settings = Settings()
```

**環境変数一覧:**

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `OTO_HOST` | `0.0.0.0` | バインドするホスト |
| `OTO_PORT` | `8000` | バインドするポート |
| `OTO_ACESTEP_ROOT` | `./ACE-Step-1.5` | ACE-Step ルートディレクトリ |
| `OTO_DIT_CONFIG` | `acestep-v15-turbo` | DiT モデル設定名 |
| `OTO_LM_MODEL` | `""` (自動選択) | LM モデルパス（例: `acestep-5Hz-lm-4B`） |
| `OTO_LM_BACKEND` | `vllm` | LM バックエンド |
| `OTO_DEVICE` | `auto` | デバイス |
| `OTO_AUDIO_DIR` | `./.cache/audio` | 生成音声の保存先 |
| `OTO_JOB_TTL` | `3600` | ジョブの有効期限（秒） |
| `OTO_QUEUE_MAX` | `100` | キューの最大サイズ |

> **補足**: `audio_output_dir` / `job_ttl_seconds` / `queue_max_size` という Python のフィールド名と、`OTO_AUDIO_DIR` / `OTO_JOB_TTL` / `OTO_QUEUE_MAX` という環境変数名は一致しないため、`Field(..., validation_alias=...)` を明示している。

---

### 4. `backend/services/job_store.py` — ジョブ状態管理

**目的**: ジョブの作成・取得・更新・削除をスレッドセーフに行うインメモリストア。ワーカースレッドと FastAPI の非同期ハンドラの両方からアクセスされるため、`threading.Lock` で排他制御する。

**依存ライブラリ**:
- `threading`: `Lock`
- `uuid`: `uuid4`
- `datetime`: `datetime`, `timezone`
- `os`: ファイル削除
- `loguru`: `logger`

```python
"""インメモリのジョブ状態管理。スレッドセーフ。"""

import os
import threading
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from loguru import logger

from backend.models.schemas import GenerateRequest, JobStatus


class _JobRecord:
    """ジョブの内部状態を保持するデータクラス。"""

    __slots__ = (
        "job_id",
        "status",
        "prompt",
        "duration",
        "bpm",
        "seed",
        "progress",
        "stage",
        "created_at",
        "completed_at",
        "error",
        "audio_path",
    )

    def __init__(self, job_id: str, request: GenerateRequest) -> None:
        self.job_id: str = job_id
        self.status: JobStatus = JobStatus.QUEUED
        self.prompt: str = request.prompt
        self.duration: int = request.duration
        self.bpm: Optional[int] = request.bpm
        self.seed: Optional[int] = request.seed
        self.progress: Optional[float] = None
        self.stage: Optional[str] = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.completed_at: Optional[datetime] = None
        self.error: Optional[str] = None
        self.audio_path: Optional[str] = None


class JobStore:
    """
    ジョブの CRUD 操作を提供するインメモリストア。

    すべてのパブリックメソッドはスレッドセーフである。
    ワーカースレッド（generate_music を実行）と FastAPI の非同期ハンドラの
    両方から同時にアクセスされる可能性があるため、Lock で排他制御する。
    """

    def __init__(self, ttl_seconds: int = 3600) -> None:
        """
        Args:
            ttl_seconds: completed/failed ジョブを保持する秒数。
                         この期間を過ぎたジョブは cleanup_expired() で削除される。
        """
        self._jobs: dict[str, _JobRecord] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds

    def create(self, request: GenerateRequest) -> str:
        """
        新規ジョブを作成し、ジョブ ID を返す。

        Args:
            request: クライアントからの生成リクエスト。

        Returns:
            生成されたジョブ ID（UUID v4 文字列）。
        """
        job_id = str(uuid4())
        record = _JobRecord(job_id, request)
        with self._lock:
            self._jobs[job_id] = record
        logger.info("ジョブ作成: job_id={}, prompt={!r}", job_id, request.prompt)
        return job_id

    def get(self, job_id: str) -> Optional[_JobRecord]:
        """
        ジョブを取得する。存在しない場合は None を返す。

        Args:
            job_id: 取得するジョブの ID。

        Returns:
            _JobRecord または None。
        """
        with self._lock:
            return self._jobs.get(job_id)

    def update_status(self, job_id: str, status: JobStatus) -> None:
        """
        ジョブの状態を更新する。

        Args:
            job_id: 更新するジョブの ID。
            status: 新しい状態。
        """
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.status = status
            logger.info("ジョブ状態更新: job_id={}, status={}", job_id, status.value)

    def update_progress(self, job_id: str, progress: float, stage: str) -> None:
        """
        ジョブの進捗を更新する。ACE-Step の progress コールバックから呼ばれる。

        Args:
            job_id: 更新するジョブの ID。
            progress: 進捗率 0.0〜1.0。
            stage: 現在の処理段階の説明文（例: "Preparing inputs...", "Decoding audio..."）。
        """
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.progress = progress
            record.stage = stage

    def delete(self, job_id: str) -> None:
        """
        ジョブをストアから削除する。

        キュー投入に失敗したときのロールバックで使用する。
        """
        with self._lock:
            removed = self._jobs.pop(job_id, None)
        if removed is not None:
            logger.info("ジョブ削除: job_id={}", job_id)

    def complete(self, job_id: str, audio_path: str) -> None:
        """
        ジョブを完了状態にする。

        Args:
            job_id: 完了するジョブの ID。
            audio_path: 生成された MP3 ファイルの絶対パス。
        """
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.status = JobStatus.COMPLETED
            record.progress = 1.0
            record.completed_at = datetime.now(timezone.utc)
            record.audio_path = audio_path
        logger.info("ジョブ完了: job_id={}, audio_path={}", job_id, audio_path)

    def fail(self, job_id: str, error: str) -> None:
        """
        ジョブを失敗状態にする。

        Args:
            job_id: 失敗したジョブの ID。
            error: エラーメッセージ。
        """
        with self._lock:
            record = self._jobs.get(job_id)
            if record is None:
                return
            record.status = JobStatus.FAILED
            record.completed_at = datetime.now(timezone.utc)
            record.error = error
        logger.error("ジョブ失敗: job_id={}, error={}", job_id, error)

    def queue_size(self) -> int:
        """QUEUED 状態のジョブ数を返す。"""
        with self._lock:
            return sum(
                1 for r in self._jobs.values() if r.status == JobStatus.QUEUED
            )

    def cleanup_expired(self) -> int:
        """
        TTL を超えた completed/failed ジョブを削除する。
        関連する音声ファイルも削除する。

        Returns:
            削除したジョブの数。
        """
        now = datetime.now(timezone.utc)
        to_delete: list[str] = []
        with self._lock:
            for job_id, record in self._jobs.items():
                if record.completed_at is None:
                    continue
                elapsed = (now - record.completed_at).total_seconds()
                if elapsed > self._ttl:
                    to_delete.append(job_id)

            for job_id in to_delete:
                record = self._jobs.pop(job_id)
                # 音声ファイルの削除
                if record.audio_path and os.path.exists(record.audio_path):
                    os.remove(record.audio_path)
                    logger.info("期限切れ音声ファイル削除: {}", record.audio_path)

        if to_delete:
            logger.info("期限切れジョブを {} 件削除した", len(to_delete))
        return len(to_delete)
```

---

### 5. `backend/services/music_generator.py` — 音楽生成ラッパー

**目的**: ACE-Step 1.5 の `generate_music()` 関数をラップし、バックエンド固有の設定（`instrumental=True`、`batch_size=1`、`audio_format="mp3"` 等）を適用する。

**使用する ACE-Step モジュール:**

| インポート | 用途 |
|-----------|------|
| `acestep.inference.generate_music` | 音楽生成のメイン関数 |
| `acestep.inference.GenerationParams` | 生成パラメータ（caption, duration, bpm 等） |
| `acestep.inference.GenerationConfig` | 生成設定（batch_size, audio_format 等） |
| `acestep.inference.GenerationResult` | 生成結果（audios, success, error 等） |
| `acestep.handler.AceStepHandler` | DiT モデルのハンドラ（型ヒント用） |
| `acestep.llm_inference.LLMHandler` | LLM ハンドラ（型ヒント用） |

**ACE-Step の `generate_music()` の呼び出し規約:**

```
generate_music(
    dit_handler,       # AceStepHandler のインスタンス（初期化済み）
    llm_handler,       # LLMHandler のインスタンス（初期化済み、または None）
    params,            # GenerationParams データクラス
    config,            # GenerationConfig データクラス
    save_dir,          # MP3 ファイルの保存先ディレクトリ（str）
    progress,          # コールバック関数: progress(value, desc="...") を受けられる callable
) -> GenerationResult
```

`GenerationResult` の構造:
- `success: bool` — 生成が成功したか
- `error: Optional[str]` — エラーメッセージ
- `audios: list[dict]` — 各要素は `{"path": str, "tensor": Tensor, "sample_rate": int, ...}`
  - `path` は保存された MP3 ファイルの絶対パス

```python
"""ACE-Step 1.5 を使用した音楽生成のラッパー。"""

from typing import TYPE_CHECKING, Callable, Optional

from loguru import logger

from backend.services.job_store import _JobRecord

if TYPE_CHECKING:
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler


def generate_and_save(
    dit_handler: "AceStepHandler",
    llm_handler: Optional["LLMHandler"],
    job: _JobRecord,
    save_dir: str,
    progress_callback: Callable[[float, str], None],
) -> str:
    """
    音楽を生成し、MP3 ファイルとして保存する。

    この関数はブロッキングであり、ThreadPoolExecutor 内で実行される。
    生成には数十秒〜数分かかる（GPU 性能に依存）。

    Args:
        dit_handler: 初期化済みの AceStepHandler インスタンス。
        llm_handler: 初期化済みの LLMHandler インスタンス（None の場合は LM を使わない）。
        job: 処理対象のジョブレコード。
        save_dir: MP3 ファイルの保存先ディレクトリ。
        progress_callback: 進捗更新コールバック。(value: float, desc: str) を受け取る。

    Returns:
        生成された MP3 ファイルの絶対パス。

    Raises:
        RuntimeError: 音楽生成に失敗した場合。
    """
    # `acestep` は遅延 import にする。main.py の import 時点で
    # ACE-Step が未解決でも、この関数が呼ばれる頃には lifespan で準備済み。
    from acestep.inference import (
        GenerationConfig,
        GenerationParams,
        GenerationResult,
        generate_music,
    )

    logger.info(
        "音楽生成開始: job_id={}, prompt={!r}, duration={}s, bpm={}",
        job.job_id,
        job.prompt,
        job.duration,
        job.bpm,
    )

    # --- 1. GenerationParams の構築 ---
    # caption: 音楽の説明文（ユーザーの prompt をそのまま使用）
    # instrumental: True（作業音なのでボーカルなし）
    # thinking: True（LM によるメタデータ自動生成を有効化）
    # duration: ユーザー指定の秒数
    # bpm: ユーザー指定 or None（None の場合 LM が自動決定）
    params = GenerationParams(
        caption=job.prompt,
        lyrics="",
        instrumental=True,
        duration=float(job.duration),
        bpm=job.bpm,
        thinking=llm_handler is not None,
        task_type="text2music",
    )

    # --- 2. GenerationConfig の構築 ---
    # batch_size: 1（1リクエストにつき1曲生成）
    # audio_format: "mp3"（ブラウザ再生用）
    # use_random_seed: seed 未指定ならランダム、指定なら固定
    if job.seed is not None:
        config = GenerationConfig(
            batch_size=1,
            use_random_seed=False,
            seeds=[job.seed],
            audio_format="mp3",
        )
    else:
        config = GenerationConfig(
            batch_size=1,
            use_random_seed=True,
            audio_format="mp3",
        )

    def _on_progress(value: float, desc: str | None = None, **_: object) -> None:
        """
        ACE-Step は progress(0.52, desc="...") のように keyword 引数で呼ぶ。
        バックエンド側では stage 文字列をそのまま JobStore に保存する。
        """
        progress_callback(value, desc or "")

    # --- 3. 音楽生成の実行 ---
    # generate_music() は内部で以下の処理を行う:
    #   Phase 1（LM）: caption からメタデータ（BPM, キー等）を生成
    #   Phase 2（DiT）: メタデータをもとに音声波形を生成
    #   Phase 3（保存）: AudioSaver で MP3 にエンコードして save_dir に保存
    result: GenerationResult = generate_music(
        dit_handler=dit_handler,
        llm_handler=llm_handler,
        params=params,
        config=config,
        save_dir=save_dir,
        progress=_on_progress,
    )

    # --- 4. 結果の確認 ---
    if not result.success:
        logger.error("音楽生成失敗: job_id={}, error={}", job.job_id, result.error)
        raise RuntimeError(f"音楽生成に失敗: {result.error}")

    if not result.audios:
        raise RuntimeError("音楽生成は成功したが、音声ファイルが見つからない")

    audio_path = result.audios[0]["path"]
    logger.info("音楽生成完了: job_id={}, path={}", job.job_id, audio_path)
    return audio_path
```

---

### 6. `backend/services/__init__.py`

```python
"""サービス層パッケージ。"""
```

---

### 7. `backend/routers/generate.py` — エンドポイント定義

**目的**: 4 つのエンドポイントを定義する。FastAPI の `APIRouter` を使用し、`/api` プレフィックスでグループ化する。

**依存ライブラリ**:
- `fastapi`: `APIRouter`, `HTTPException`, `Request`
- `fastapi.responses`: `FileResponse`

**注意点**:
- `Request` オブジェクト経由で `app.state` にアクセスする。`app.state` にはモデルハンドラやジョブストアが格納されている（`main.py` の lifespan で初期化）。
- `FileResponse` は `Content-Type` を自動設定するが、MP3 の場合は明示的に `media_type="audio/mpeg"` を指定する。
- `asyncio.Queue.full()` の事前チェックだけでは競合を防げないため、投入時は `put_nowait()` と `asyncio.QueueFull` を使って原子的に扱う。
- `stage` の文言は ACE-Step 側実装で変わりうる。API クライアントは `status` のみで状態分岐する。

```python
"""音楽生成エンドポイント。"""

import asyncio

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse
from loguru import logger

from backend.models.schemas import (
    GenerateJobResponse,
    GenerateRequest,
    HealthResponse,
    JobStatus,
    JobStatusResponse,
)

# プレフィックス /api を設定。main.py で app.include_router(router) する。
router = APIRouter(prefix="/api", tags=["generate"])


@router.post(
    "/generate",
    response_model=GenerateJobResponse,
    status_code=202,
    summary="音楽生成ジョブを投入する",
)
async def create_generate_job(
    request_body: GenerateRequest,
    request: Request,
) -> GenerateJobResponse:
    """
    テキストプロンプトを受け取り、音楽生成ジョブをキューに投入する。
    レスポンスは即時返却される（生成完了を待たない）。
    """
    job_store = request.app.state.job_store
    job_queue: asyncio.Queue = request.app.state.job_queue

    # ジョブ作成 → キューに投入
    job_id = job_store.create(request_body)
    try:
        job_queue.put_nowait(job_id)
    except asyncio.QueueFull:
        job_store.delete(job_id)
        raise HTTPException(
            status_code=503,
            detail="キューが満杯である。しばらく待ってからリトライしてほしい",
        )
    logger.info("ジョブをキューに投入: job_id={}", job_id)

    return GenerateJobResponse(
        job_id=job_id,
        status=JobStatus.QUEUED,
        message="ジョブを受け付けた",
    )


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    summary="ジョブの状態を確認する",
)
async def get_job_status(job_id: str, request: Request) -> JobStatusResponse:
    """
    ジョブの現在の状態と進捗を返す。
    クライアントはこのエンドポイントを 2 秒間隔でポーリングする。
    """
    job_store = request.app.state.job_store
    record = job_store.get(job_id)

    if record is None:
        raise HTTPException(status_code=404, detail="ジョブが見つからない")

    return JobStatusResponse(
        job_id=record.job_id,
        status=record.status,
        progress=record.progress,
        stage=record.stage,
        created_at=record.created_at,
        completed_at=record.completed_at,
        error=record.error,
    )


@router.get(
    "/jobs/{job_id}/audio",
    summary="生成された MP3 をダウンロードする",
    responses={
        200: {"content": {"audio/mpeg": {}}, "description": "MP3 ファイル"},
        404: {"description": "ジョブが見つからない"},
        409: {"description": "ジョブが未完了"},
    },
)
async def download_audio(job_id: str, request: Request) -> FileResponse:
    """生成完了した MP3 ファイルを返す。"""
    job_store = request.app.state.job_store
    record = job_store.get(job_id)

    if record is None:
        raise HTTPException(status_code=404, detail="ジョブが見つからない")

    if record.status != JobStatus.COMPLETED:
        raise HTTPException(
            status_code=409,
            detail=f"ジョブがまだ完了していない（現在の状態: {record.status.value}）",
        )

    if not record.audio_path:
        raise HTTPException(status_code=500, detail="音声ファイルのパスが未設定")

    return FileResponse(
        path=record.audio_path,
        media_type="audio/mpeg",
        filename=f"oto_{job_id}.mp3",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="サーバーの状態を確認する",
)
async def health_check(request: Request) -> HealthResponse:
    """サーバーとモデルの状態を返す。"""
    import torch

    job_queue: asyncio.Queue = request.app.state.job_queue

    # GPU 情報の取得
    if torch.cuda.is_available():
        gpu_name = torch.cuda.get_device_name(0)
        vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
    elif hasattr(torch, "xpu") and torch.xpu.is_available():
        gpu_name = torch.xpu.get_device_name(0)
        vram_gb = torch.xpu.get_device_properties(0).total_memory / (1024**3)
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        gpu_name = "Apple Silicon (MPS)"
        try:
            vram_gb = torch.mps.recommended_max_memory() / (1024**3)
        except Exception:
            vram_gb = 0.0
    else:
        gpu_name = "CPU"
        vram_gb = 0.0

    job_store = request.app.state.job_store
    model_loaded = request.app.state.model_loaded

    return HealthResponse(
        status="ok",
        model_loaded=model_loaded,
        gpu=gpu_name,
        vram_gb=round(vram_gb, 1),
        queue_size=job_queue.qsize(),
    )
```

---

### 8. `backend/routers/__init__.py`

```python
"""ルーターパッケージ。"""
```

---

### 9. `backend/main.py` — アプリケーションエントリポイント

**目的**: FastAPI アプリの生成、モデル初期化、バックグラウンドワーカーの管理を行う。

**lifespan の処理順序（重要）:**

1. `uv run` で起動し、path dependency として `ace-step` を解決する
2. 必要であれば `sys.path` に ACE-Step ルートを追加する（補助策）
3. 音声出力ディレクトリの作成
4. GPU 検出と `GPUConfig` のグローバル設定
5. `AceStepHandler` の初期化（DiT + VAE + テキストエンコーダの読み込み）
6. `LLMHandler` の初期化（5Hz LM の読み込み）
7. `JobStore` と `asyncio.Queue` の作成
8. ワーカータスクの起動
9. 期限切れジョブの定期クリーンアップタスクの起動

**使用する ACE-Step モジュール:**

| インポート | 初期化時の呼び出し |
|-----------|------------------|
| `acestep.handler.AceStepHandler` | `handler.initialize_service(project_root=..., config_path=..., device=...)` |
| `acestep.llm_inference.LLMHandler` | `handler.initialize(checkpoint_dir=..., lm_model_path=..., backend=..., device=...)` |
| `acestep.gpu_config.get_gpu_config` | GPU ティアを自動検出して `GPUConfig` を返す |
| `acestep.gpu_config.set_global_gpu_config` | 検出した `GPUConfig` をグローバルに設定（ACE-Step 内部で参照される） |
| `acestep.gpu_config.get_recommended_lm_model` | GPU ティアに応じた推奨 LM モデル名を返す |
| `acestep.model_downloader.get_checkpoints_dir` | チェックポイントディレクトリのパスを返す |

**`AceStepHandler.initialize_service()` のシグネチャ:**

```python
def initialize_service(
    self,
    project_root: str,     # ACE-Step-1.5 のルートパス（絶対パス）
    config_path: str,      # DiT モデル設定名（例: "acestep-v15-turbo"）
    device: str = "auto",  # "auto" で GPU 自動検出
) -> Tuple[str, bool]:     # (ステータスメッセージ, 成功フラグ)
```

**`LLMHandler.initialize()` のシグネチャ:**

```python
def initialize(
    self,
    checkpoint_dir: str,   # チェックポイントディレクトリの絶対パス
    lm_model_path: str,    # LM モデル名（例: "acestep-5Hz-lm-4B"）
    backend: str = "vllm", # "vllm" または "pt"
    device: str = "auto",
) -> Tuple[str, bool]:     # (ステータスメッセージ, 成功フラグ)
```

```python
"""FastAPI アプリケーションのエントリポイント。"""

import asyncio
import sys
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.config import settings
from backend.models.schemas import JobStatus
from backend.routers.generate import router
from backend.services.job_store import JobStore
from backend.services.music_generator import generate_and_save


# ---------------------------------------------------------------------------
# バックグラウンドワーカー
# ---------------------------------------------------------------------------
async def _queue_worker(app: FastAPI) -> None:
    """
    バックグラウンドワーカー。キューからジョブ ID を取り出し、順次処理する。

    1 つのジョブが完了するまで次のジョブは開始しない（逐次処理）。
    GPU メモリを複数ジョブで共有することによる OOM を防ぐため、
    意図的に並列化していない。
    """
    loop = asyncio.get_event_loop()
    job_store: JobStore = app.state.job_store
    executor: ThreadPoolExecutor = app.state.executor

    logger.info("ワーカー起動: ジョブの受付を開始する")

    while True:
        # キューからジョブ ID を取得（ブロッキング待機）
        job_id: str = await app.state.job_queue.get()
        record = job_store.get(job_id)
        if record is None:
            logger.warning("ジョブが見つからない: job_id={}", job_id)
            continue

        # 状態を running に更新
        job_store.update_status(job_id, JobStatus.RUNNING)

        try:
            # ブロッキングな音楽生成処理をスレッドプールで実行
            # generate_and_save() は数十秒〜数分かかる
            audio_path = await loop.run_in_executor(
                executor,
                generate_and_save,
                app.state.dit_handler,
                app.state.llm_handler,
                record,
                str(settings.audio_output_path),
                # progress コールバック: ACE-Step が進捗を通知するたびに呼ばれる
                lambda p, s: job_store.update_progress(job_id, p, s),
            )
            job_store.complete(job_id, audio_path=audio_path)
        except Exception as e:
            logger.exception("ジョブ処理中にエラー: job_id={}", job_id)
            job_store.fail(job_id, error=str(e))


async def _cleanup_worker(app: FastAPI) -> None:
    """期限切れジョブを 5 分ごとに削除する。"""
    job_store: JobStore = app.state.job_store
    while True:
        await asyncio.sleep(300)  # 5 分間隔
        try:
            deleted = job_store.cleanup_expired()
            if deleted > 0:
                logger.info("クリーンアップ完了: {} 件のジョブを削除", deleted)
        except Exception:
            logger.exception("クリーンアップ中にエラー")


# ---------------------------------------------------------------------------
# lifespan（起動・終了処理）
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    アプリケーションのライフスパン管理。

    起動時にモデルを読み込み、終了時にリソースを解放する。
    モデルの読み込みには数分かかるため、起動ログを確認すること。
    """
    logger.info("=== oto-factory バックエンド起動開始 ===")

    # --- 1. sys.path に ACE-Step ルートを追加 ---
    # 標準運用では `uv run` により import は解決される。
    # この追加は、ローカル直接実行時の補助策として残す。
    acestep_root = str(settings.acestep_root_path)
    if acestep_root not in sys.path:
        sys.path.insert(0, acestep_root)
        logger.info("sys.path に追加: {}", acestep_root)

    # --- 2. 音声出力ディレクトリの作成 ---
    settings.audio_output_path.mkdir(parents=True, exist_ok=True)
    logger.info("音声出力ディレクトリ: {}", settings.audio_output_path)

    # --- 3. ACE-Step モジュールのインポート（sys.path 追加後） ---
    from acestep.gpu_config import (
        get_gpu_config,
        get_recommended_lm_model,
        set_global_gpu_config,
    )
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler
    from acestep.model_downloader import get_checkpoints_dir

    # --- 4. GPU 検出 ---
    gpu_config = get_gpu_config()
    set_global_gpu_config(gpu_config)
    logger.info(
        "GPU 検出完了: tier={}, memory={:.1f}GB",
        gpu_config.tier,
        gpu_config.gpu_memory_gb,
    )

    # --- 5. DiT ハンドラの初期化 ---
    logger.info("DiT モデル初期化中 (config={})...", settings.dit_config)
    dit_handler = AceStepHandler()
    status_msg, ok = dit_handler.initialize_service(
        project_root=acestep_root,
        config_path=settings.dit_config,
        device=settings.device,
    )
    if not ok:
        logger.error("DiT モデルの初期化に失敗: {}", status_msg)
        raise RuntimeError(f"DiT モデルの初期化に失敗: {status_msg}")
    logger.info("DiT モデル初期化完了: {}", status_msg)

    # --- 6. LLM ハンドラの初期化 ---
    # checkpoint_dir には ACE-Step ルートではなく checkpoints ディレクトリを渡す。
    checkpoint_dir = str(get_checkpoints_dir())
    lm_model = settings.lm_model or get_recommended_lm_model(gpu_config) or ""
    llm_handler: LLMHandler | None = None

    if lm_model:
        logger.info("LLM 初期化中 (model={}, backend={})...", lm_model, settings.lm_backend)
        llm_handler = LLMHandler()
        llm_status, llm_ok = llm_handler.initialize(
            checkpoint_dir=checkpoint_dir,
            lm_model_path=lm_model,
            backend=settings.lm_backend,
            device=settings.device,
        )
        if not llm_ok:
            logger.warning("LLM の初期化に失敗（DiT のみモードで続行）: {}", llm_status)
            llm_handler = None
        else:
            logger.info("LLM 初期化完了: {}", llm_status)
    else:
        logger.info("LLM モデル未設定のため、DiT のみモードで起動")

    # --- 7. app.state にハンドラと管理オブジェクトを格納 ---
    app.state.dit_handler = dit_handler
    app.state.llm_handler = llm_handler
    app.state.model_loaded = True
    app.state.job_store = JobStore(ttl_seconds=settings.job_ttl_seconds)
    app.state.job_queue = asyncio.Queue(maxsize=settings.queue_max_size)
    app.state.executor = ThreadPoolExecutor(max_workers=1)

    # --- 8. バックグラウンドタスクの起動 ---
    worker_task = asyncio.create_task(_queue_worker(app))
    cleanup_task = asyncio.create_task(_cleanup_worker(app))

    logger.info("=== oto-factory バックエンド起動完了 (port={}) ===", settings.port)

    yield  # ← ここでアプリケーションが稼働する

    # --- 終了処理 ---
    logger.info("シャットダウン開始...")
    worker_task.cancel()
    cleanup_task.cancel()
    app.state.executor.shutdown(wait=False)
    logger.info("シャットダウン完了")


# ---------------------------------------------------------------------------
# FastAPI アプリの生成
# ---------------------------------------------------------------------------
app = FastAPI(
    title="oto-factory",
    description="作業音リアルタイム生成 API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS ミドルウェア（ブラウザからの直接アクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 開発時は全許可
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(router)


# ---------------------------------------------------------------------------
# CLI エントリポイント
# ---------------------------------------------------------------------------
def cli_main() -> None:
    """pyproject.toml の [project.scripts] から呼ばれるエントリポイント。"""
    import uvicorn

    logger.info("oto-factory バックエンドを起動: {}:{}", settings.host, settings.port)
    uvicorn.run(
        "backend.main:app",
        host=settings.host,
        port=settings.port,
        workers=1,  # GPU を使うため worker は 1 に固定
    )


if __name__ == "__main__":
    cli_main()
```

---

### 10. `backend/__init__.py`

```python
"""oto-factory バックエンドパッケージ。"""
```

---

## 処理フローの詳細

### リクエストからレスポンスまでの完全なフロー

```
1. ブラウザが POST /api/generate を送信
   ↓
2. FastAPI が GenerateRequest を自動バリデーション
   - prompt が空 → 422 Unprocessable Entity
   - duration が範囲外 → 422 Unprocessable Entity
   ↓
3. routers/generate.py の create_generate_job() が実行
   a. job_store.create(request) でジョブ登録 → job_id 取得
   b. job_queue.put_nowait(job_id) でキューに投入（満杯ならジョブ登録をロールバック）
   c. 202 Accepted + {job_id, status: "queued"} を返却
   ↓
4. ブラウザが GET /api/jobs/{job_id} をポーリング開始（2 秒間隔）
   ↓
5. _queue_worker がキューからジョブを取り出し
   a. job_store.update_status(job_id, RUNNING)
   b. ThreadPoolExecutor で generate_and_save() を実行
   ↓
6. generate_and_save() が ACE-Step を呼び出し
   a. GenerationParams を構築（caption=prompt, instrumental=True, ...）
   b. GenerationConfig を構築（batch_size=1, audio_format="mp3"）
   c. generate_music() を呼び出し
      ├─ Phase 1: 必要に応じて LLM がメタデータ生成（BPM, キー, スケール等）
      ├─ Phase 2: DiT が音声波形を生成
      │   → progress(0.51, desc="Preparing inputs...")
      │   → progress(0.52, desc="Generating music (batch size: 1)...")
      │   → progress(0.80, desc="Decoding audio...")
      └─ Phase 3: AudioSaver が MP3 にエンコードして save_dir に保存
          → progress(0.99, desc="Preparing audio data...")
   d. result.audios[0]["path"] を返す（MP3 の絶対パス）
   ↓
7. _queue_worker が job_store.complete(job_id, audio_path) で完了登録
   ↓
8. ブラウザのポーリングが status: "completed" を検出
   ↓
9. ブラウザが GET /api/jobs/{job_id}/audio を送信
   ↓
10. FileResponse が MP3 ファイルを返却
    Content-Type: audio/mpeg
    Content-Disposition: attachment; filename="oto_{job_id}.mp3"
```

---

## CORS 設定

ブラウザからの直接アクセスを許可するため、CORS ミドルウェアを設定する。

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 開発時は全許可、本番環境では制限する
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

---

## クライアント側の使用例

### cURL

```bash
# 1. ジョブ投入
curl -X POST http://localhost:8000/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "シンプルなハウスミュージック", "duration": 60}'

# レスポンス: {"job_id": "abc123...", "status": "queued", "message": "ジョブを受け付けた"}

# 2. 状態確認（ポーリング）
curl http://localhost:8000/api/jobs/abc123...

# レスポンス: {"job_id": "abc123...", "status": "running", "progress": 0.52, "stage": "Generating music (batch size: 1)...", ...}

# 3. 完了後に音声ダウンロード
curl -o output.mp3 http://localhost:8000/api/jobs/abc123.../audio
```

### JavaScript（ブラウザ）

```javascript
// 1. ジョブ投入
const res = await fetch("/api/generate", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    prompt: "シンプルなハウスミュージック",
    duration: 60,
  }),
});
const { job_id } = await res.json();

// 2. ポーリングで完了を待つ
const poll = async () => {
  const status = await fetch(`/api/jobs/${job_id}`).then((r) => r.json());
  if (status.status === "completed") {
    // 3. 音声を再生
    const audio = new Audio(`/api/jobs/${job_id}/audio`);
    audio.play();
  } else if (status.status === "failed") {
    console.error("生成失敗:", status.error);
  } else {
    console.log(
      `進捗: ${(status.progress * 100).toFixed(0)}% - ${status.stage}`
    );
    setTimeout(poll, 2000); // 2秒ごとにポーリング
  }
};
poll();
```

---

## セットアップと起動方法

```bash
cd /content/oto-factory

# 1. サブモジュールの初期化（初回のみ）
git submodule update --init --recursive

# 2. 依存関係のインストール（ACE-Step 含む全依存関係）
uv sync

# 3. バックエンドの起動
uv run oto-backend

# または直接 uvicorn で起動
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

起動後、`http://localhost:8000/docs` で Swagger UI（自動生成された API ドキュメント）にアクセスできる。

---

## 生成時間の目安

ACE-Step 1.5 の生成性能（1分間の楽曲、batch_size=1）：

| GPU | 推定生成時間 |
|-----|------------|
| A100 (40GB) | 5〜10秒 |
| RTX 3090 (24GB) | 15〜30秒 |
| T4 (16GB) | 30〜60秒 |

※ LM 推論（メタデータ生成）を含む。vLLM バックエンド使用時。

---

## 今後の拡張候補

以下は現時点では実装しないが、将来的に追加を検討する機能である。

- **WebSocket による進捗通知**: ポーリングの代わりにリアルタイム進捗通知
- **ジョブ履歴の永続化**: SQLite 等によるジョブ履歴の保存
- **キャッシュ**: 同一プロンプト・同一シードの結果をキャッシュ
- **複数バリエーション生成**: batch_size > 1 で複数候補を返す
- **ストリーミング配信**: 生成済み部分から逐次配信
- **認証**: API キーによるアクセス制御
