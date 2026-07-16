"""ゴールデンテストデータのスキーマ（YAML）。
過去のAI回答は正解として扱わない。ユーザーが提供する元サイトの画面・出力結果
（画像・テキスト）のみを正解データとする。未確認項目は status: unverified とする。
"""
from __future__ import annotations

from dataclasses import dataclass, field

REQUIRED_TOP_LEVEL_FIELDS = ["name", "gender", "birth_date", "birth_place", "source", "confirmed_on", "status"]


@dataclass
class GoldenTestEntry:
    name: str
    gender: str
    birth_date: str  # YYYY-MM-DD
    birth_time: str | None  # HH:MM or null
    birth_place: str
    source: str  # 出典（例: "suimei.starcrawler.net スクリーンショット 2026-07-16"）
    confirmed_on: str  # 確認日 YYYY-MM-DD
    status: str  # verified | unverified
    notes: str = ""

    expected_year_pillar: str | None = None
    expected_month_pillar: str | None = None
    expected_day_pillar: str | None = None
    expected_hour_pillar: str | None = None
    expected_day_master: str | None = None
    expected_five_elements: str | None = None
    expected_center_star: str | None = None
    expected_juudai_shusei: dict = field(default_factory=dict)
    expected_juuni_daijuusei: dict = field(default_factory=dict)
    expected_tenchuusatsu: list = field(default_factory=list)
    expected_major_luck_start: str | None = None
    expected_major_cycles: list = field(default_factory=list)

    @staticmethod
    def from_dict(d: dict) -> "GoldenTestEntry":
        missing = [f for f in REQUIRED_TOP_LEVEL_FIELDS if f not in d]
        if missing:
            raise ValueError(f"必須項目が不足しています: {missing}")
        known_fields = {f.name for f in GoldenTestEntry.__dataclass_fields__.values()}
        filtered = {k: v for k, v in d.items() if k in known_fields}
        return GoldenTestEntry(**filtered)
