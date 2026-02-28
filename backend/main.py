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
