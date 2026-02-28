"""アプリケーション設定。環境変数から読み込む。"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    環境変数から設定を読み込む。

    プレフィックス OTO_ を使用する。
    例: OTO_PORT=8000 → self.port = 8000
    """

    # サーバー設定
    host: str = "0.0.0.0"
    port: int = 8000

    # ACE-Step 1.5 設定
    acestep_root: str = "./ACE-Step-1.5"
    dit_config: str = "acestep-v15-turbo"
    lm_model: str = ""           # 空文字の場合は GPU に応じて自動選択
    lm_backend: str = "vllm"     # "vllm" または "pt"
    device: str = "auto"         # "auto", "cuda", "mps", "cpu"

    # 生成した音声の保存先
    audio_output_dir: str = Field(
        default="./.cache/audio",
        validation_alias="OTO_AUDIO_DIR",
    )

    # ジョブ管理
    job_ttl_seconds: int = Field(
        default=3600,
        validation_alias="OTO_JOB_TTL",
    )
    queue_max_size: int = Field(
        default=100,
        validation_alias="OTO_QUEUE_MAX",
    )

    model_config = SettingsConfigDict(env_prefix="OTO_")

    @property
    def acestep_root_path(self) -> Path:
        """ACE-Step ルートの Path オブジェクトを返す。"""
        return Path(self.acestep_root).resolve()

    @property
    def audio_output_path(self) -> Path:
        """音声出力ディレクトリの Path オブジェクトを返す。"""
        return Path(self.audio_output_dir).resolve()


# シングルトンインスタンス。各モジュールからインポートして使用する。
settings = Settings()
