"""
作業音リアルタイム生成プロトタイプ - Web UI

Flask ベースの Web インターフェースを提供する。
"""

import logging
import time
import json
from pathlib import Path
from threading import Thread, Lock
from flask import Flask, render_template, jsonify, Response, send_file
from datetime import datetime

from config import (
    API_BASE_URL,
    DEFAULT_PROMPT,
    SEGMENT_SECONDS,
    PREFETCH_TARGET,
    OUTPUT_DIR,
)
from ace_client import ACEStepClient
from generator_loop import GeneratorLoop

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Flask アプリケーション
app = Flask(__name__)

# グローバル状態
class AppState:
    def __init__(self):
        self.client = None
        self.generator = None
        self.running = False
        self.start_time = None
        self.segments_played = 0
        self.logs = []
        self.max_logs = 100
        self.lock = Lock()

    def add_log(self, level, message):
        """ログを追加"""
        with self.lock:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logs.append({
                "timestamp": timestamp,
                "level": level,
                "message": message
            })
            # 最大ログ数を超えたら古いものを削除
            if len(self.logs) > self.max_logs:
                self.logs = self.logs[-self.max_logs:]

    def get_status(self):
        """現在の状態を取得"""
        with self.lock:
            if not self.running or not self.generator:
                return {
                    "running": False,
                    "segments_generated": 0,
                    "segments_played": self.segments_played,
                    "queue_size": 0,
                    "uptime": 0,
                }

            uptime = int(time.time() - self.start_time) if self.start_time else 0

            # 生成済みセグメント数を確認
            segments_generated = self.generator.segment_counter
            queue_size = self.generator.queue_size()

            return {
                "running": True,
                "segments_generated": segments_generated,
                "segments_played": self.segments_played,
                "queue_size": queue_size,
                "uptime": uptime,
                "api_url": API_BASE_URL,
                "prompt": DEFAULT_PROMPT,
                "segment_duration": SEGMENT_SECONDS,
                "prefetch_target": PREFETCH_TARGET,
            }

state = AppState()


# カスタムログハンドラー
class WebUILogHandler(logging.Handler):
    """Web UI 用のログハンドラー"""

    def emit(self, record):
        try:
            msg = self.format(record)
            state.add_log(record.levelname, msg)
        except Exception:
            self.handleError(record)


# ルートハンドラーを追加
web_handler = WebUILogHandler()
web_handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))
logging.getLogger().addHandler(web_handler)


def generator_worker():
    """生成ワーカースレッド"""
    state.add_log("INFO", "生成ループを開始しました")

    # クライアント初期化
    state.client = ACEStepClient(base_url=API_BASE_URL)
    state.generator = GeneratorLoop(
        client=state.client,
        prompt=DEFAULT_PROMPT,
        segment_duration=SEGMENT_SECONDS,
        prefetch_target=PREFETCH_TARGET,
    )

    # 生成ループ開始
    state.generator.start()
    state.start_time = time.time()

    # 初期セグメント待機
    state.add_log("INFO", "初期セグメント生成を待機中...")
    while state.running and state.generator.queue_size() == 0:
        time.sleep(1)

    if not state.running:
        state.add_log("INFO", "起動中にキャンセルされました")
        state.generator.stop()
        return

    state.add_log("INFO", "初期セグメント準備完了")

    # 再生ループ（実際には生成のみ、再生は省略）
    while state.running:
        # キューサイズを確認
        queue_size = state.generator.queue_size()

        if queue_size > 0:
            # セグメントを取得（実際には再生しない）
            segment_file = state.generator.get_next_segment(timeout=5.0)

            if segment_file:
                state.segments_played += 1
                state.add_log(
                    "INFO",
                    f"セグメント#{state.segments_played}: {segment_file.name} "
                    f"(キュー残: {state.generator.queue_size()})"
                )
        else:
            state.add_log("WARNING", "キューが空です。待機中...")

        time.sleep(2)

    # 停止処理
    state.add_log("INFO", "生成ループを停止しました")
    if state.generator:
        state.generator.stop()


@app.route("/")
def index():
    """メインページ"""
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    """ステータス API"""
    return jsonify(state.get_status())


@app.route("/api/logs")
def api_logs():
    """ログ API"""
    with state.lock:
        return jsonify(state.logs[-50:])  # 最新50件


@app.route("/api/start", methods=["POST"])
def api_start():
    """生成開始 API"""
    if state.running:
        return jsonify({"error": "Already running"}), 400

    state.running = True
    state.segments_played = 0
    state.logs.clear()

    # ワーカースレッド起動
    thread = Thread(target=generator_worker, daemon=True)
    thread.start()

    return jsonify({"status": "started"})


@app.route("/api/stop", methods=["POST"])
def api_stop():
    """生成停止 API"""
    if not state.running:
        return jsonify({"error": "Not running"}), 400

    state.running = False
    state.add_log("INFO", "停止要求を受信しました")

    return jsonify({"status": "stopped"})


@app.route("/api/segments")
def api_segments():
    """セグメント一覧 API"""
    segments = []
    for file in sorted(OUTPUT_DIR.glob("segment_*.wav")):
        segments.append({
            "name": file.name,
            "size": file.stat().st_size,
            "mtime": file.stat().st_mtime,
        })
    return jsonify(segments)


@app.route("/api/download/<filename>")
def api_download(filename):
    """セグメントダウンロード API"""
    file_path = OUTPUT_DIR / filename
    if not file_path.exists() or not file_path.name.startswith("segment_"):
        return jsonify({"error": "File not found"}), 404

    return send_file(file_path, as_attachment=True)


def main():
    """メインエントリポイント"""
    logger.info("Web UI を起動しています...")
    logger.info(f"URL: http://0.0.0.0:8090")
    logger.info("Ctrl+C で終了")

    app.run(host="0.0.0.0", port=8090, debug=False)


if __name__ == "__main__":
    main()
