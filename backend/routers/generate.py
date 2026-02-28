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
        # キューが満杯の場合はジョブ登録をロールバックして 503 を返す
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
