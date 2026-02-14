"""
プロトタイプの動作確認テスト

2セグメント生成して、キューイングと先読み生成が正しく動作するか確認する。
"""

import logging
import time
from ace_client import ACEStepClient
from generator_loop import GeneratorLoop
from config import DEFAULT_PROMPT

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """プロトタイプ動作確認"""
    logger.info("=== プロトタイプ動作確認開始 ===")

    # ACE-Step API クライアント初期化
    client = ACEStepClient()

    # 生成ループ初期化（短いセグメント、少ない目標数）
    generator = GeneratorLoop(
        client=client,
        prompt=DEFAULT_PROMPT,
        segment_duration=10,  # 10秒のセグメント
        prefetch_target=2,    # 2セグメントまで生成
    )

    # 生成ループ開始
    logger.info("生成ループ開始")
    generator.start()

    # 生成を待機
    logger.info("セグメント生成を待機中...")
    time.sleep(30)  # 30秒待機（2セグメント生成されるはず）

    # キューサイズを確認
    queue_size = generator.queue_size()
    logger.info(f"キューサイズ: {queue_size}")

    if queue_size > 0:
        logger.info("✅ セグメント生成成功！")

        # 最初のセグメントを取得
        segment_path = generator.get_next_segment(timeout=5)
        if segment_path:
            logger.info(f"セグメント取得: {segment_path}")
            logger.info(f"ファイルサイズ: {segment_path.stat().st_size / 1024:.1f} KB")
        else:
            logger.warning("セグメント取得失敗")
    else:
        logger.error("❌ セグメント生成失敗")

    # 生成ループ停止
    logger.info("生成ループ停止")
    generator.stop()

    logger.info("=== プロトタイプ動作確認完了 ===")


if __name__ == "__main__":
    main()
