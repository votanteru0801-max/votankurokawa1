"""一括登録文章の簡易パーサー（規則ベース）。

本番（ANTHROPIC_MODE=live）ではClaudeがNLUを行い register_person ツールの
構造化引数として抽出するのが主経路だが、本モジュールは以下の目的で用意する。

1. ANTHROPIC_MODE=mock でのローカル動作・自動テストを可能にする
2. Claudeの抽出結果に対する簡易クロスチェック（将来の拡張余地）

「山田花子、2003年5月10日、10時30分、福岡県福岡市、女性」のような
カンマ区切りの一括入力を主眼に置いた、意図的にシンプルな実装。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, time

from app.schemas.person import Gender, PersonCategory

CATEGORY_KEYWORDS: dict[str, PersonCategory] = {
    "採用候補者": PersonCategory.CANDIDATE,
    "候補者": PersonCategory.CANDIDATE,
    "社員": PersonCategory.EMPLOYEE,
    "外部コンサルタント": PersonCategory.EXTERNAL_CONSULTANT,
    "コンサルタント": PersonCategory.EXTERNAL_CONSULTANT,
    "取引先": PersonCategory.BUSINESS_PARTNER,
    "講師": PersonCategory.INSTRUCTOR,
    "パートナー": PersonCategory.PARTNER,
}

PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]

DATE_RE = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
TIME_RE = re.compile(r"(\d{1,2})時(\d{1,2})?分?")
TIME_COLON_RE = re.compile(r"(\d{1,2}):(\d{2})")


@dataclass
class ParsedRegistration:
    category: PersonCategory | None = None
    name: str | None = None
    birth_date: date | None = None
    birth_time: time | None = None
    birth_time_unknown: bool = True
    prefecture: str | None = None
    city: str | None = None
    gender: Gender = Gender.UNKNOWN
    unparsed_tokens: list[str] = field(default_factory=list)

    def missing_required_fields(self) -> list[str]:
        missing = []
        if not self.category:
            missing.append("人物区分")
        if not self.name:
            missing.append("氏名")
        if not self.birth_date:
            missing.append("生年月日")
        if not self.gender or self.gender == Gender.UNKNOWN:
            missing.append("性別")
        return missing


def parse_bulk_registration_text(text: str) -> ParsedRegistration:
    result = ParsedRegistration()

    for keyword, category in CATEGORY_KEYWORDS.items():
        if keyword in text:
            result.category = category
            break

    if "。" in text:
        _, _, remainder = text.partition("。")
    else:
        remainder = text

    tokens = [t.strip() for t in re.split("[、,，]", remainder) if t.strip()]

    for token in tokens:
        date_match = DATE_RE.search(token)
        if date_match:
            y, m, d = map(int, date_match.groups())
            try:
                result.birth_date = date(y, m, d)
            except ValueError:
                pass
            continue

        time_match = TIME_RE.search(token) or TIME_COLON_RE.search(token)
        if time_match:
            h = int(time_match.group(1))
            mi = int(time_match.group(2)) if time_match.group(2) else 0
            if 0 <= h < 24 and 0 <= mi < 60:
                result.birth_time = time(h, mi)
                result.birth_time_unknown = False
            continue

        if token in ("男性", "男"):
            result.gender = Gender.MALE
            continue
        if token in ("女性", "女"):
            result.gender = Gender.FEMALE
            continue

        matched_pref = next((p for p in PREFECTURES if token.startswith(p)), None)
        if matched_pref:
            result.prefecture = matched_pref
            city_part = token[len(matched_pref):].strip()
            if city_part:
                result.city = city_part
            continue

        # カテゴリキーワードのみのトークンは無視
        if token in CATEGORY_KEYWORDS:
            continue

        if result.name is None and not any(ch.isdigit() for ch in token):
            result.name = token
            continue

        result.unparsed_tokens.append(token)

    if result.birth_time is None:
        result.birth_time_unknown = True

    return result
