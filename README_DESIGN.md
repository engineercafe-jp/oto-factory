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
| `bpm` | `int \| null` | `null` | テンポ。null の場合は LM が自動決定 |
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

1. リクエストバリデーション（prompt 必須、duration 範囲チェック）
2. UUID v4 でジョブ ID を生成
3. ジョブストアに `queued` 状態で登録
4. `asyncio.Queue` にジョブを投入
5. ジョブ ID を即時返却（202 Accepted）

---

### 2. `GET /api/jobs/{job_id}` — ジョブ状態確認

ジョブの現在の状態と進捗を返す。クライアントはこのエンドポイントをポーリングして完了を待つ。

**レスポンス（200 OK）:**

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "running",
  "progress": 0.45,
  "stage": "DiT 推論中 (step 4/8)",
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
| `stage` | `str \| null` | 現在の処理段階の説明 |
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
  "detail": "ジョブがまだ完了していない",
  "status": "running"
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

## データモデル

### リクエストモデル

```python
class GenerateRequest(BaseModel):
    """音楽生成リクエスト。"""
    prompt: str = Field(
        ...,
        min_length=1,
        max_length=512,
        description="生成する音楽の説明文",
        examples=["シンプルなハウスミュージック"],
    )
    duration: int = Field(
        default=60,
        ge=10,
        le=600,
        description="生成する音楽の長さ（秒）",
    )
    bpm: Optional[int] = Field(
        default=None,
        ge=30,
        le=300,
        description="テンポ。null の場合は自動決定",
    )
    seed: Optional[int] = Field(
        default=None,
        description="乱数シード。null の場合はランダム",
    )
```

### ジョブモデル

```python
class JobStatus(str, Enum):
    """ジョブの状態。"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(BaseModel):
    """ジョブの状態と結果。"""
    job_id: str
    status: JobStatus
    progress: Optional[float] = None
    stage: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    audio_path: Optional[str] = None  # 内部用：MP3 ファイルパス
```

---

## 内部アーキテクチャ

### モジュール構成

```
oto-factory/
├── ACE-Step-1.5/              # サブモジュール（既存）
├── backend/
│   ├── __init__.py
│   ├── main.py                # FastAPI アプリケーション・エントリポイント
│   ├── routers/
│   │   ├── __init__.py
│   │   └── generate.py        # /api/generate, /api/jobs エンドポイント
│   ├── services/
│   │   ├── __init__.py
│   │   ├── music_generator.py # ACE-Step 呼び出しラッパー
│   │   └── job_store.py       # ジョブ状態管理（インメモリ）
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic モデル定義
│   └── config.py              # 設定値の管理
├── pyproject.toml             # プロジェクト設定
└── README_DESIGN.md           # 本ファイル
```

### 各モジュールの責務

| モジュール | 責務 |
|-----------|------|
| `main.py` | FastAPI アプリ生成、ライフスパンイベントでモデル初期化・ワーカー起動 |
| `routers/generate.py` | エンドポイント定義、リクエストバリデーション |
| `services/music_generator.py` | ACE-Step の `generate_music()` 呼び出し、MP3 保存 |
| `services/job_store.py` | ジョブの CRUD、進捗更新、期限切れジョブの清掃 |
| `models/schemas.py` | `GenerateRequest`, `Job`, `JobStatus` 等の Pydantic モデル |
| `config.py` | 環境変数からの設定読み込み（モデルパス、ポート、ワーカー数等） |

---

### ジョブキューとワーカー

```python
# main.py（概念的な実装）
@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフスパン管理。"""
    # 起動時：モデルの初期化
    app.state.dit_handler = AceStepHandler()
    app.state.dit_handler.initialize_service(
        project_root=settings.acestep_root,
        config_path=settings.dit_config,
        device="auto",
    )
    app.state.llm_handler = LLMHandler()
    app.state.llm_handler.initialize(
        project_root=settings.acestep_root,
        model_path=settings.lm_model,
    )

    # ジョブキューとワーカーの起動
    app.state.job_queue = asyncio.Queue(maxsize=100)
    app.state.job_store = JobStore()
    app.state.executor = ThreadPoolExecutor(max_workers=1)
    worker_task = asyncio.create_task(
        queue_worker(app)
    )

    yield

    # 終了時：ワーカーの停止とリソース解放
    worker_task.cancel()
    app.state.executor.shutdown(wait=False)


async def queue_worker(app: FastAPI):
    """バックグラウンドワーカー。キューからジョブを取り出して順次処理する。"""
    loop = asyncio.get_event_loop()
    while True:
        job_id = await app.state.job_queue.get()
        job = app.state.job_store.get(job_id)

        # 状態を running に更新
        app.state.job_store.update_status(job_id, JobStatus.RUNNING)

        try:
            # ブロッキング処理をスレッドプールで実行
            result = await loop.run_in_executor(
                app.state.executor,
                generate_and_save,
                app.state.dit_handler,
                app.state.llm_handler,
                job,
                lambda p, s: app.state.job_store.update_progress(job_id, p, s),
            )
            app.state.job_store.complete(job_id, audio_path=result)
        except Exception as e:
            app.state.job_store.fail(job_id, error=str(e))
```

### 音楽生成フロー

```python
# services/music_generator.py（概念的な実装）
def generate_and_save(
    dit_handler: AceStepHandler,
    llm_handler: LLMHandler,
    job: Job,
    progress_callback: Callable[[float, str], None],
) -> str:
    """
    音楽を生成し、MP3 ファイルとして保存する。

    Returns:
        生成された MP3 ファイルのパス。
    """
    # 1. GenerationParams を構築
    params = GenerationParams(
        caption=job.prompt,
        lyrics="",
        instrumental=True,       # 作業音なのでインストゥルメンタル
        duration=job.duration,
        bpm=job.bpm or -1,
        thinking=True,           # LM による自動メタデータ生成
        task_type="text2music",
    )
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

    # 2. 音楽生成（数十秒〜数分かかる）
    result = generate_music(
        dit_handler=dit_handler,
        llm_handler=llm_handler,
        params=params,
        config=config,
        save_dir=settings.audio_output_dir,
        progress=progress_callback,
    )

    if not result.success:
        raise RuntimeError(f"音楽生成に失敗: {result.error}")

    # 3. 生成された MP3 ファイルのパスを返す
    return result.audios[0]["path"]
```

---

### ジョブストア

```python
# services/job_store.py（概念的な実装）
class JobStore:
    """インメモリのジョブ状態管理。スレッドセーフ。"""

    def __init__(self, ttl_seconds: int = 3600):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds  # ジョブの有効期限（デフォルト1時間）

    def create(self, job_id: str, request: GenerateRequest) -> Job:
        """新規ジョブを作成する。"""

    def get(self, job_id: str) -> Optional[Job]:
        """ジョブを取得する。"""

    def update_status(self, job_id: str, status: JobStatus) -> None:
        """ジョブの状態を更新する。"""

    def update_progress(self, job_id: str, progress: float, stage: str) -> None:
        """ジョブの進捗を更新する。"""

    def complete(self, job_id: str, audio_path: str) -> None:
        """ジョブを完了状態にする。"""

    def fail(self, job_id: str, error: str) -> None:
        """ジョブを失敗状態にする。"""

    def cleanup_expired(self) -> int:
        """期限切れジョブを削除し、関連音声ファイルも削除する。"""
```

---

## 設定

### 環境変数

| 変数名 | デフォルト | 説明 |
|--------|-----------|------|
| `OTO_HOST` | `0.0.0.0` | バインドするホスト |
| `OTO_PORT` | `8000` | バインドするポート |
| `OTO_ACESTEP_ROOT` | `./ACE-Step-1.5` | ACE-Step ルートディレクトリ |
| `OTO_DIT_CONFIG` | `acestep-v15-turbo` | DiT モデル設定 |
| `OTO_LM_MODEL` | `acestep-5Hz-lm-4B` | LM モデルパス |
| `OTO_LM_BACKEND` | `vllm` | LM バックエンド（`vllm` / `pt`） |
| `OTO_AUDIO_DIR` | `./.cache/audio` | 生成音声の保存先 |
| `OTO_JOB_TTL` | `3600` | ジョブの有効期限（秒） |
| `OTO_QUEUE_MAX` | `100` | キューの最大サイズ |

### 設定クラス

```python
# config.py
class Settings(BaseSettings):
    """アプリケーション設定。環境変数から読み込む。"""
    host: str = "0.0.0.0"
    port: int = 8000
    acestep_root: str = "./ACE-Step-1.5"
    dit_config: str = "acestep-v15-turbo"
    lm_model: str = "acestep-5Hz-lm-4B"
    lm_backend: str = "vllm"
    audio_output_dir: str = "./.cache/audio"
    job_ttl_seconds: int = 3600
    queue_max_size: int = 100

    model_config = SettingsConfigDict(env_prefix="OTO_")
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

# レスポンス: {"job_id": "abc123...", "status": "queued", ...}

# 2. 状態確認（ポーリング）
curl http://localhost:8000/api/jobs/abc123...

# レスポンス: {"status": "running", "progress": 0.45, ...}

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
  const status = await fetch(`/api/jobs/${job_id}`).then(r => r.json());
  if (status.status === "completed") {
    // 3. 音声を再生
    const audio = new Audio(`/api/jobs/${job_id}/audio`);
    audio.play();
  } else if (status.status === "failed") {
    console.error("生成失敗:", status.error);
  } else {
    console.log(`進捗: ${(status.progress * 100).toFixed(0)}% - ${status.stage}`);
    setTimeout(poll, 2000);  // 2秒ごとにポーリング
  }
};
poll();
```

---

## 起動方法

```bash
cd /content/oto-factory

# 依存関係のインストール
uv sync

# バックエンドの起動
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

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
