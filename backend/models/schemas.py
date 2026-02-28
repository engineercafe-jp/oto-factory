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
