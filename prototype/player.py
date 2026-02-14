"""
作業音リアルタイム生成プロトタイプ - 再生制御

生成された音声セグメントを連続再生する。
"""

import logging
import subprocess
import time
from pathlib import Path
from typing import Optional
from threading import Thread, Event

logger = logging.getLogger(__name__)


class AudioPlayer:
    """音声プレイヤー"""

    def __init__(self):
        """初期化"""
        self.stop_event = Event()
        self.thread: Optional[Thread] = None
        self.current_segment: Optional[Path] = None

    def play(self, audio_file: Path) -> bool:
        """
        音声ファイルを再生する

        Args:
            audio_file: 音声ファイルパス

        Returns:
            success: 再生成功フラグ
        """
        if not audio_file.exists():
            logger.error(f"音声ファイルが存在しません: {audio_file}")
            return False

        self.current_segment = audio_file
        logger.info(f"再生開始: {audio_file.name}")

        try:
            # ffplay で再生（ウィンドウなし、自動終了）
            result = subprocess.run(
                [
                    "ffplay",
                    "-nodisp",  # ウィンドウ非表示
                    "-autoexit",  # 再生終了後に自動終了
                    "-loglevel", "quiet",  # ログ非表示
                    str(audio_file),
                ],
                check=True,
                capture_output=True,
            )

            logger.info(f"再生完了: {audio_file.name}")
            return True

        except subprocess.CalledProcessError as e:
            logger.error(f"再生エラー: {e}")
            return False

        except FileNotFoundError:
            logger.error("ffplay が見つかりません。インストールしてください: sudo apt install ffmpeg")
            return False

        finally:
            self.current_segment = None

    def is_playing(self) -> bool:
        """再生中かどうかを返す"""
        return self.current_segment is not None
