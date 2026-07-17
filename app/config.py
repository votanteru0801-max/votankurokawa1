"""アプリ設定。環境変数から読み込む。秘密情報は絶対にログ出力しない。"""
from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Mode(str, Enum):
    MOCK = "mock"
    LIVE = "live"


class YearPillarBoundary(str, Enum):
    """年柱を切り替える基準。"""

    RISSHUN = "risshun"  # 立春（節切り）※初期設定
    JAN1 = "jan1"  # 西暦1月1日基準（一部流派）


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "local"
    tz: str = "Asia/Tokyo"
    log_level: str = "INFO"

    line_mode: Mode = Mode.MOCK
    google_sheets_mode: Mode = Mode.MOCK
    anthropic_mode: Mode = Mode.MOCK

    allowed_line_user_id: str = "U0000000000000000000000000000000"

    line_channel_secret: str = ""
    line_channel_access_token: str = ""

    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_max_tool_retries: int = 2

    google_application_credentials: str = ""
    # Secret Files機能が使えない環境向け: サービスアカウントJSONの中身をそのまま
    # 環境変数として渡す場合はこちらを使う（設定されていればファイルパスより優先）。
    google_service_account_json: str = ""
    hr_spreadsheet_id: str = "14Qz4S4s3CGOrjFsijOvjXy542BkG3DJ3gLYzZFAXWvg"

    database_url: str = "postgresql+psycopg://kuroeda:kuroeda@db:5432/kuroeda"

    calc_policy_version: str = "2026.1"
    calc_year_pillar_boundary: YearPillarBoundary = YearPillarBoundary.RISSHUN
    calc_day_boundary_hour: int = 0
    calc_true_solar_time_correction: bool = False

    undo_window_minutes: int = 1440


@lru_cache
def get_settings() -> Settings:
    return Settings()


class LineLimits:
    """LINE Messaging APIの制限値。仕様変更時はここだけ調整する。
    2026年7月時点の公式ドキュメント(developers.line.biz)に基づく想定値。
    本番運用前に docs/line-setup.md の手順で最新仕様を再確認すること。
    """

    MAX_TEXT_MESSAGE_LENGTH = 5000
    MAX_MESSAGES_PER_REPLY = 5
    SAFE_CHUNK_LENGTH = 1800  # 分割送信時、読みやすさを優先した1通あたりの目安文字数
