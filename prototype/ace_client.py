"""
作業音リアルタイム生成プロトタイプ - ACE-Step API クライアント

/release_task と /query_result を呼び出すクライアント実装である。
"""

import requests
import time
import json
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

            # APIレスポンスの構造を確認
            if isinstance(result, dict) and "data" in result:
                # ラッパー形式の場合
                data = result.get("data", {})
                task_id = data.get("task_id")
            else:
                # 直接レスポンスの場合
                task_id = result.get("task_id")

            if task_id:
                logger.info(f"タスク受付成功: task_id={task_id}")
                return task_id
            else:
                logger.error(f"タスクIDが取得できませんでした: {result}")
                return None

        except requests.HTTPError as e:
            logger.error(
                f"タスク投入失敗 (HTTP {e.response.status_code}): {e.response.text[:200]}"
            )
            return None
        except requests.RequestException as e:
            logger.error(f"タスク投入失敗 (ネットワークエラー): {e}")
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
        # API は task_id_list（リスト形式）を期待している
        payload = {"task_id_list": [task_id]}

        try:
            response = self.session.post(url, json=payload, timeout=10)
            response.raise_for_status()

            result = response.json()

            # APIレスポンスの構造を確認
            # ラッパー形式: {"data": [{"task_id": "...", "result": "...", "status": 0|1|2}], ...}
            if isinstance(result, dict) and "data" in result:
                data_list = result.get("data", [])
                if not data_list or len(data_list) == 0:
                    logger.debug(f"タスク未登録: task_id={task_id}")
                    return None

                # 最初の要素を取得
                item = data_list[0]
                status = item.get("status")

                # result フィールドは JSON 文字列の場合がある
                result_data = item.get("result", "{}")
                if isinstance(result_data, str):
                    try:
                        result_data = json.loads(result_data) if result_data else {}
                    except json.JSONDecodeError:
                        result_data = {}

                # result_data がリストの場合は最初の要素を取得
                if isinstance(result_data, list) and len(result_data) > 0:
                    result_data = result_data[0]

                data = result_data if isinstance(result_data, dict) else {}
                data["status"] = status
                data["task_id"] = task_id
            else:
                # 直接レスポンスの場合
                status = result.get("status")
                data = result

            if status == 1:  # 成功
                logger.info(f"タスク完了: task_id={task_id}")

                # 音声ファイルを保存
                # API は "file" フィールドに音声のパスを返す
                audio_path = data.get("audio_path") or data.get("file")
                if save_to and audio_path:
                    # audio_path から音声をダウンロード
                    audio_url = f"{self.base_url}{audio_path}"

                    logger.debug(f"音声ダウンロード: {audio_url}")
                    audio_response = self.session.get(audio_url, timeout=30)
                    audio_response.raise_for_status()

                    save_to.write_bytes(audio_response.content)
                    logger.info(f"音声ファイル保存: {save_to}")
                    data["local_audio_path"] = str(save_to)

                return data

            elif status == 2:  # 失敗
                error_msg = data.get("error", data.get("message", "Unknown error"))
                logger.error(f"タスク失敗: task_id={task_id}, error={error_msg}")
                return data

            else:  # 実行中または不明
                logger.debug(f"タスク実行中: task_id={task_id}, status={status}")
                return data

        except requests.HTTPError as e:
            logger.error(
                f"結果取得失敗 (HTTP {e.response.status_code}): task_id={task_id}, {e.response.text[:200]}"
            )
            return None
        except requests.RequestException as e:
            logger.error(f"結果取得失敗 (ネットワークエラー): task_id={task_id}, error={e}")
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
