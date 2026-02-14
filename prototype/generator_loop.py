"""
作業音リアルタイム生成プロトタイプ - 先読み生成ロジック

セグメントを先読み生成してキューに格納する。
"""

import logging
import time
from pathlib import Path
from typing import List, Optional
from queue import Queue
from threading import Thread, Event

from ace_client import ACEStepClient
from config import (
    SEGMENT_SECONDS,
    PREFETCH_TARGET,
    DEFAULT_PROMPT,
    OUTPUT_DIR,
)

logger = logging.getLogger(__name__)


class GeneratorLoop:
    """先読み生成ループ"""

    def __init__(
        self,
        client: ACEStepClient,
        prompt: str = DEFAULT_PROMPT,
        segment_duration: int = SEGMENT_SECONDS,
        prefetch_target: int = PREFETCH_TARGET,
    ):
        """
        初期化

        Args:
            client: ACE-Step API クライアント
            prompt: 生成プロンプト
            segment_duration: セグメントの長さ（秒）
            prefetch_target: キュー目標本数
        """
        self.client = client
        self.prompt = prompt
        self.segment_duration = segment_duration
        self.prefetch_target = prefetch_target

        self.queue: Queue[Path] = Queue()
        self.stop_event = Event()
        self.thread: Optional[Thread] = None
        self.segment_counter = 0

    def start(self):
        """生成ループを開始する"""
        if self.thread and self.thread.is_alive():
            logger.warning("生成ループは既に実行中です")
            return

        self.stop_event.clear()
        self.thread = Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        logger.info("生成ループを開始しました")

    def stop(self):
        """生成ループを停止する"""
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=10)
        logger.info("生成ループを停止しました")

    def get_next_segment(self, timeout: Optional[float] = None) -> Optional[Path]:
        """
        次のセグメントを取得する

        Args:
            timeout: タイムアウト（秒）

        Returns:
            audio_path: 音声ファイルパス（キューが空の場合は None）
        """
        try:
            return self.queue.get(timeout=timeout)
        except:
            return None

    def queue_size(self) -> int:
        """キューのサイズを返す"""
        return self.queue.qsize()

    def _run_loop(self):
        """生成ループのメイン処理"""
        logger.info(f"先読み生成ループ開始: target={self.prefetch_target}, duration={self.segment_duration}s")

        consecutive_failures = 0
        max_consecutive_failures = 5

        while not self.stop_event.is_set():
            try:
                # キューの残量をチェック
                current_size = self.queue.qsize()
                logger.debug(f"キュー残量: {current_size}/{self.prefetch_target}")

                if current_size >= self.prefetch_target:
                    # 十分にキューがある場合は待機
                    time.sleep(2)
                    continue

                # 新しいセグメントを生成
                success = self._generate_segment()

                if success:
                    consecutive_failures = 0  # 成功したらリセット
                else:
                    consecutive_failures += 1
                    # 連続失敗時はバックオフ
                    backoff_time = min(2 ** consecutive_failures, 60)  # 最大60秒
                    logger.warning(
                        f"セグメント生成失敗（連続{consecutive_failures}回）。"
                        f"{backoff_time}秒待機します"
                    )
                    time.sleep(backoff_time)

                    # 連続失敗が多すぎる場合は警告
                    if consecutive_failures >= max_consecutive_failures:
                        logger.error(
                            f"連続{consecutive_failures}回失敗しました。"
                            "API サーバーの状態を確認してください"
                        )
                        time.sleep(10)  # 長めに待機

            except Exception as e:
                logger.error(f"生成ループエラー: {e}", exc_info=True)
                time.sleep(5)  # エラー時は少し待機

    def _generate_segment(self) -> bool:
        """
        1つのセグメントを生成してキューに追加する

        Returns:
            success: 生成成功フラグ
        """
        self.segment_counter += 1
        segment_id = self.segment_counter

        logger.info(f"セグメント#{segment_id} 生成開始")
        start_time = time.time()

        # タスク投入
        task_id = self.client.release_task(
            prompt=self.prompt,
            duration=self.segment_duration,
        )

        if not task_id:
            logger.error(f"セグメント#{segment_id} タスク投入失敗")
            return False  # 失敗を返す

        # 保存先ファイル名
        output_file = OUTPUT_DIR / f"segment_{segment_id:04d}.wav"

        # タスク完了を待機
        result = self.client.wait_for_completion(
            task_id=task_id,
            save_to=output_file,
            timeout=300,
        )

        if result and result.get("status") == 1:
            elapsed = time.time() - start_time
            logger.info(
                f"セグメント#{segment_id} 生成完了: {output_file.name} ({elapsed:.1f}秒)"
            )

            # キューに追加
            self.queue.put(output_file)
            logger.info(f"キューに追加: サイズ={self.queue.qsize()}")
            return True  # 成功

        else:
            logger.error(f"セグメント#{segment_id} 生成失敗")
            return False  # 失敗
