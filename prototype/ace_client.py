"""
作業音リアルタイム生成プロトタイプ - ACE-Step API クライアント

/release_task と /query_result を呼び出すクライアント実装である。
"""

import requests
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

from config import (
    API_BASE_URL,
    LM_MODEL_PATH,
    LM_BACKEND,
    CONFIG_PATH,
    POLL_INTERVAL_SEC,
    MAX_RETRY,
    OUTPUT_DIR,
)

logger = logging.getLogger(__name__)


class ACEStepClient:
    """ACE-Step API クライアント"""

    def __init__(self, base_url: str = API_BASE_URL):
        """
        初期化

        Args:
            base_url: API のベース URL
        """
        self.base_url = base_url
        self.session = requests.Session()

    def release_task(
        self,
        prompt: str,
        duration: int,
        task_type: str = "text2music",
        thinking: bool = True,
    ) -> Optional[str]:
        """
        音楽生成タスクを投入する

        Args:
            prompt: 生成プロンプト
            duration: 音声の長さ（秒）
            task_type: タスクタイプ
            thinking: LM の思考モードを有効にするか

        Returns:
            task_id: タスクID（失敗時は None）
        """
        url = f"{self.base_url}/release_task"
        payload = {
            "task_type": task_type,
            "text": prompt,
            "thinking": thinking,
            "lm_backend": LM_BACKEND,
            "lm_model_path": LM_MODEL_PATH,
            "config_path": CONFIG_PATH,
            "audio_duration": duration,
        }

        try:
            logger.info(f"タスク投入: prompt='{prompt[:50]}...', duration={duration}s")
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            task_id = result.get("task_id")

            if task_id:
                logger.info(f"タスク受付成功: task_id={task_id}")
                return task_id
            else:
                logger.error(f"タスクIDが取得できませんでした: {result}")
                return None

        except requests.RequestException as e:
            logger.error(f"タスク投入失敗: {e}")
            return None

    def query_result(
        self, task_id: str, save_to: Optional[Path] = None
    ) -> Optional[Dict[str, Any]]:
        """
        タスクの結果をポーリングする

        Args:
            task_id: タスクID
            save_to: 音声ファイルの保存先（指定時のみ保存）

        Returns:
            result: タスク結果（status, audio_path など）
        """
        url = f"{self.base_url}/query_result"
        payload = {"task_id": task_id}

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()
            status = result.get("status")

            if status == 1:  # 成功
                logger.info(f"タスク完了: task_id={task_id}")

                # 音声ファイルを保存
                if save_to and "audio" in result:
                    audio_data = result["audio"]
                    if isinstance(audio_data, str):
                        # Base64 エンコードされている場合
                        import base64
                        audio_bytes = base64.b64decode(audio_data)
                        save_to.write_bytes(audio_bytes)
                        logger.info(f"音声ファイル保存: {save_to}")
                        result["audio_path"] = str(save_to)

                return result

            elif status == 2:  # 失敗
                logger.error(f"タスク失敗: task_id={task_id}, error={result.get('error')}")
                return result

            else:  # 実行中または不明
                logger.debug(f"タスク実行中: task_id={task_id}, status={status}")
                return result

        except requests.RequestException as e:
            logger.error(f"結果取得失敗: task_id={task_id}, error={e}")
            return None

    def wait_for_completion(
        self,
        task_id: str,
        save_to: Optional[Path] = None,
        timeout: int = 300,
    ) -> Optional[Dict[str, Any]]:
        """
        タスクが完了するまで待機する

        Args:
            task_id: タスクID
            save_to: 音声ファイルの保存先
            timeout: タイムアウト（秒）

        Returns:
            result: タスク結果（成功時）、None（失敗時）
        """
        start_time = time.time()
        retry_count = 0

        while time.time() - start_time < timeout:
            result = self.query_result(task_id, save_to=save_to)

            if result is None:
                retry_count += 1
                if retry_count > MAX_RETRY:
                    logger.error(f"最大リトライ回数超過: task_id={task_id}")
                    return None
                time.sleep(POLL_INTERVAL_SEC)
                continue

            status = result.get("status")

            if status == 1:  # 成功
                return result
            elif status == 2:  # 失敗
                return None
            else:  # 実行中
                time.sleep(POLL_INTERVAL_SEC)

        logger.error(f"タイムアウト: task_id={task_id}")
        return None
