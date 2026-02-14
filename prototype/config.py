"""
作業音リアルタイム生成プロトタイプ - 設定ファイル

定数と設定値を管理する。
"""

import os
from pathlib import Path

# ACE-Step API サーバー設定
API_HOST = os.getenv("ACESTEP_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("ACESTEP_API_PORT", "8001"))
API_BASE_URL = f"http://{API_HOST}:{API_PORT}"

# モデル設定
LM_MODEL_PATH = os.getenv("LM_MODEL_PATH", "acestep-5Hz-lm-0.6B")
LM_BACKEND = os.getenv("LM_BACKEND", "vllm")
CONFIG_PATH = os.getenv("CONFIG_PATH", "acestep-v15-turbo")

# セグメント生成設定
SEGMENT_SECONDS = int(os.getenv("SEGMENT_SECONDS", "30"))  # 1セグメントの秒数
PREFETCH_TARGET = int(os.getenv("PREFETCH_TARGET", "3"))   # キュー目標本数

# ポーリング設定
POLL_INTERVAL_SEC = float(os.getenv("POLL_INTERVAL_SEC", "1.5"))  # 結果確認間隔
MAX_RETRY = int(os.getenv("MAX_RETRY", "2"))  # 最大リトライ回数

# プロンプト設定
DEFAULT_PROMPT = os.getenv(
    "DEFAULT_PROMPT",
    "穏やかな環境音、集中作業に適した雰囲気、ローファイ、アンビエント"
)

# 音声出力ディレクトリ
OUTPUT_DIR = Path("/content/oto-factory/prototype/generated_audio")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ログレベル
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
