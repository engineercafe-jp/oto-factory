"""
作業音リアルタイム生成プロトタイプ - メインアプリケーション

先読み生成と連続再生を統合したエントリポイントである。
"""

import logging
import time
import signal
import sys
from pathlib import Path

from config import (
    API_BASE_URL,
    DEFAULT_PROMPT,
    SEGMENT_SECONDS,
    PREFETCH_TARGET,
    LOG_LEVEL,
)
from ace_client import ACEStepClient
from generator_loop import GeneratorLoop
from player import AudioPlayer

# ログ設定
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


class WorkSoundApp:
    """作業音リアルタイム生成アプリケーション"""

    def __init__(self):
        """初期化"""
        self.client = ACEStepClient(base_url=API_BASE_URL)
        self.generator = GeneratorLoop(
            client=self.client,
            prompt=DEFAULT_PROMPT,
            segment_duration=SEGMENT_SECONDS,
            prefetch_target=PREFETCH_TARGET,
        )
        self.player = AudioPlayer()
        self.running = True

        # シグナルハンドラー設定
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, sig, frame):
        """シグナルハンドラー（Ctrl+C など）"""
        logger.info("停止シグナルを受信しました")
        self.running = False

    def run(self):
        """アプリケーションを実行する"""
        logger.info("=" * 60)
        logger.info("作業音リアルタイム生成プロトタイプ")
        logger.info("=" * 60)
        logger.info(f"API URL: {API_BASE_URL}")
        logger.info(f"プロンプト: {DEFAULT_PROMPT}")
        logger.info(f"セグメント長: {SEGMENT_SECONDS}秒")
        logger.info(f"先読み目標: {PREFETCH_TARGET}本")
        logger.info("=" * 60)

        # 生成ループを開始
        self.generator.start()

        # 初期セグメントが生成されるまで待機
        logger.info("初期セグメント生成を待機中...")
        while self.running and self.generator.queue_size() == 0:
            time.sleep(1)

        if not self.running:
            logger.info("起動中にキャンセルされました")
            self.generator.stop()
            return

        logger.info("初期セグメント準備完了。再生を開始します")
        logger.info("=" * 60)

        # 連続再生ループ
        segment_count = 0
        start_time = time.time()

        while self.running:
            # 次のセグメントを取得
            segment_file = self.generator.get_next_segment(timeout=5.0)

            if segment_file is None:
                logger.warning("キューが空です。セグメント生成を待機中...")
                time.sleep(2)
                continue

            # 再生
            segment_count += 1
            queue_size = self.generator.queue_size()
            elapsed_time = time.time() - start_time

            logger.info(
                f"[{segment_count}] 再生: {segment_file.name} | "
                f"キュー残: {queue_size} | 経過時間: {elapsed_time:.0f}秒"
            )

            success = self.player.play(segment_file)

            if not success:
                logger.error("再生に失敗しました")
                time.sleep(1)

        # 終了処理
        logger.info("=" * 60)
        logger.info("アプリケーションを終了します")
        self.generator.stop()
        logger.info(f"総再生セグメント数: {segment_count}")
        logger.info(f"総実行時間: {time.time() - start_time:.1f}秒")
        logger.info("=" * 60)


def main():
    """メインエントリポイント"""
    app = WorkSoundApp()

    try:
        app.run()
    except Exception as e:
        logger.error(f"予期しないエラー: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
