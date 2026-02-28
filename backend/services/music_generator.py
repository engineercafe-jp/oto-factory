"""ACE-Step 1.5 を使用した音楽生成のラッパー。"""

from typing import TYPE_CHECKING, Callable, Optional

from loguru import logger

from backend.services.job_store import _JobRecord

if TYPE_CHECKING:
    from acestep.handler import AceStepHandler
    from acestep.llm_inference import LLMHandler


def generate_and_save(
    dit_handler: "AceStepHandler",
    llm_handler: Optional["LLMHandler"],
    job: _JobRecord,
    save_dir: str,
    progress_callback: Callable[[float, str], None],
) -> str:
    """
    音楽を生成し、MP3 ファイルとして保存する。

    この関数はブロッキングであり、ThreadPoolExecutor 内で実行される。
    生成には数十秒〜数分かかる（GPU 性能に依存）。

    Args:
        dit_handler: 初期化済みの AceStepHandler インスタンス。
        llm_handler: 初期化済みの LLMHandler インスタンス（None の場合は LM を使わない）。
        job: 処理対象のジョブレコード。
        save_dir: MP3 ファイルの保存先ディレクトリ。
        progress_callback: 進捗更新コールバック。(value: float, desc: str) を受け取る。

    Returns:
        生成された MP3 ファイルの絶対パス。

    Raises:
        RuntimeError: 音楽生成に失敗した場合。
    """
    # `acestep` は遅延 import にする。main.py の import 時点で
    # ACE-Step が未解決でも、この関数が呼ばれる頃には lifespan で準備済み。
    from acestep.inference import (
        GenerationConfig,
        GenerationParams,
        GenerationResult,
        generate_music,
    )

    logger.info(
        "音楽生成開始: job_id={}, prompt={!r}, duration={}s, bpm={}",
        job.job_id,
        job.prompt,
        job.duration,
        job.bpm,
    )

    # --- 1. GenerationParams の構築 ---
    # caption: 音楽の説明文（ユーザーの prompt をそのまま使用）
    # instrumental: True（作業音なのでボーカルなし）
    # thinking: True（LM によるメタデータ自動生成を有効化）
    # duration: ユーザー指定の秒数
    # bpm: ユーザー指定 or None（None の場合 LM が自動決定）
    params = GenerationParams(
        caption=job.prompt,
        lyrics="",
        instrumental=True,
        duration=float(job.duration),
        bpm=job.bpm,
        thinking=llm_handler is not None,
        task_type="text2music",
    )

    # --- 2. GenerationConfig の構築 ---
    # batch_size: 1（1リクエストにつき1曲生成）
    # audio_format: "mp3"（ブラウザ再生用）
    # use_random_seed: seed 未指定ならランダム、指定なら固定
    if job.seed is not None:
        config = GenerationConfig(
            batch_size=1,
            use_random_seed=False,
            seeds=[job.seed],
            audio_format="mp3",
        )
    else:
        config = GenerationConfig(
            batch_size=1,
            use_random_seed=True,
            audio_format="mp3",
        )

    def _on_progress(value: float, desc: str | None = None, **_: object) -> None:
        """
        ACE-Step は progress(0.52, desc="...") のように keyword 引数で呼ぶ。
        バックエンド側では stage 文字列をそのまま JobStore に保存する。
        """
        progress_callback(value, desc or "")

    # --- 3. 音楽生成の実行 ---
    # generate_music() は内部で以下の処理を行う:
    #   Phase 1（LM）: caption からメタデータ（BPM, キー等）を生成
    #   Phase 2（DiT）: メタデータをもとに音声波形を生成
    #   Phase 3（保存）: AudioSaver で MP3 にエンコードして save_dir に保存
    result: GenerationResult = generate_music(
        dit_handler=dit_handler,
        llm_handler=llm_handler,
        params=params,
        config=config,
        save_dir=save_dir,
        progress=_on_progress,
    )

    # --- 4. 結果の確認 ---
    if not result.success:
        logger.error("音楽生成失敗: job_id={}, error={}", job.job_id, result.error)
        raise RuntimeError(f"音楽生成に失敗: {result.error}")

    if not result.audios:
        raise RuntimeError("音楽生成は成功したが、音声ファイルが見つからない")

    audio_path = result.audios[0]["path"]
    logger.info("音楽生成完了: job_id={}, path={}", job.job_id, audio_path)
    return audio_path
