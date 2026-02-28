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
