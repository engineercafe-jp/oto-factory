"""
単一セグメント生成テスト

修正した ace_client.py が正しく動作するか確認する。
"""

import logging
from pathlib import Path
from ace_client import ACEStepClient
from config import OUTPUT_DIR, DEFAULT_PROMPT

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


def main():
    """単一セグメント生成テスト"""
    logger.info("=== 単一セグメント生成テスト開始 ===")

    # クライアント初期化
    client = ACEStepClient()

    # タスク投入
    logger.info(f"プロンプト: {DEFAULT_PROMPT}")
    task_id = client.release_task(
        prompt=DEFAULT_PROMPT,
        duration=10,  # 短い時間でテスト
    )

    if not task_id:
        logger.error("タスク投入失敗")
        return

    logger.info(f"タスクID: {task_id}")

    # 保存先ファイル
    output_file = OUTPUT_DIR / "test_segment.wav"
    logger.info(f"保存先: {output_file}")

    # タスク完了を待機
    result = client.wait_for_completion(
        task_id=task_id,
        save_to=output_file,
        timeout=300,
    )

    if result and result.get("status") == 1:
        logger.info("✅ テスト成功！")
        logger.info(f"結果データ: {result}")
        logger.info(f"音声ファイル: {result.get('local_audio_path')}")
    else:
        logger.error("❌ テスト失敗")
        if result:
            logger.error(f"Status: {result.get('status')}")
            logger.error(f"結果データ: {result}")
            logger.error(f"Error: {result.get('error')}")


if __name__ == "__main__":
    main()
