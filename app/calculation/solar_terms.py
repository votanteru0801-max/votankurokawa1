"""太陽黄経に基づく二十四節気（うち月柱境界に使う12節）の計算。

Jean Meeus "Astronomical Algorithms" に記載された低精度太陽視黄経の公式
（誤差およそ0.01度、公開されている天文計算の標準的公式であり特定サイトの
コードを複製したものではない）を用いて、対象年に最も近い節入り日時を
二分探索で求める。ΔT（TT-UT差, 現代は約70秒程度）は無視しており、
日付単位の判定には影響しないが、節入り時刻が深夜0時付近の場合は数分単位の
誤差が生じ得る。本番運用前にゴールデンテストで日付境界付近のケースを
必ず確認すること。
"""
from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")

# 節(立春から30度刻み)のおおよそのカレンダー上の月日（探索の初期値としてのみ使用）
_APPROX_MONTH_DAY: dict[int, tuple[int, int]] = {
    315: (2, 4),   # 立春 -> 寅月開始
    345: (3, 5),   # 驚蟄 -> 卯月開始
    15: (4, 5),    # 清明 -> 辰月開始
    45: (5, 5),    # 立夏 -> 巳月開始
    75: (6, 5),    # 芒種 -> 午月開始
    105: (7, 7),   # 小暑 -> 未月開始
    135: (8, 7),   # 立秋 -> 申月開始
    165: (9, 7),   # 白露 -> 酉月開始
    195: (10, 8),  # 寒露 -> 戌月開始
    225: (11, 7),  # 立冬 -> 亥月開始
    255: (12, 7),  # 大雪 -> 子月開始
    285: (1, 5),   # 小寒 -> 丑月開始
}


def julian_day(dt_utc: datetime) -> float:
    """UTC datetimeからユリウス日を計算する（Meeus標準式）。"""
    y, m = dt_utc.year, dt_utc.month
    d = dt_utc.day + (dt_utc.hour + dt_utc.minute / 60 + dt_utc.second / 3600) / 24
    if m <= 2:
        y -= 1
        m += 12
    a = y // 100
    b = 2 - a + a // 4
    return int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5


def solar_apparent_longitude(jd: float) -> float:
    """太陽の視黄経（度, 0-360）を低精度公式で計算する。"""
    t = (jd - 2451545.0) / 36525.0
    l0 = 280.46646 + 36000.76983 * t + 0.0003032 * t**2
    m = 357.52911 + 35999.05029 * t - 0.0001537 * t**2
    mr = math.radians(m % 360)
    c = (
        (1.914602 - 0.004817 * t - 0.000014 * t**2) * math.sin(mr)
        + (0.019993 - 0.000101 * t) * math.sin(2 * mr)
        + 0.000289 * math.sin(3 * mr)
    )
    true_long = (l0 + c) % 360
    omega = 125.04 - 1934.136 * t
    apparent = (true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))) % 360
    return apparent


def _signed_diff(current: float, target: float) -> float:
    """current - target を -180〜180の範囲に正規化する。"""
    return ((current - target + 180) % 360) - 180


def find_term_datetime_utc(year: int, longitude_deg: float) -> datetime:
    """指定年について、太陽黄経が longitude_deg になる瞬間(UTC)を二分探索で求める。"""
    month, day = _APPROX_MONTH_DAY[round(longitude_deg) % 360]
    guess = datetime(year, month, day, 12, 0, 0)
    lo = guess - timedelta(days=10)
    hi = guess + timedelta(days=10)

    f_lo = _signed_diff(solar_apparent_longitude(julian_day(lo)), longitude_deg)
    f_hi = _signed_diff(solar_apparent_longitude(julian_day(hi)), longitude_deg)
    # 単調増加のはずだが、区間外(符号同じ)の場合は幅を広げて再試行する
    widen = 0
    while f_lo > 0 or f_hi < 0:
        widen += 1
        if widen > 3:
            break
        lo -= timedelta(days=10)
        hi += timedelta(days=10)
        f_lo = _signed_diff(solar_apparent_longitude(julian_day(lo)), longitude_deg)
        f_hi = _signed_diff(solar_apparent_longitude(julian_day(hi)), longitude_deg)

    for _ in range(60):
        mid = lo + (hi - lo) / 2
        f_mid = _signed_diff(solar_apparent_longitude(julian_day(mid)), longitude_deg)
        if f_mid < 0:
            lo = mid
        else:
            hi = mid
    return lo + (hi - lo) / 2


def find_term_datetime_jst(year: int, longitude_deg: float) -> datetime:
    """JST（Asia/Tokyo）のtz-aware datetimeで節入り瞬間を返す。"""
    utc_dt = find_term_datetime_utc(year, longitude_deg).replace(tzinfo=ZoneInfo("UTC"))
    return utc_dt.astimezone(JST)


def risshun_jst(year: int) -> datetime:
    """指定西暦年の立春（年柱境界の既定基準）をJSTで返す。"""
    return find_term_datetime_jst(year, 315)


def month_term_boundaries_around(birth_dt_jst: datetime) -> list[tuple[int, datetime]]:
    """birth_dt_jst 前後で月柱境界となる12節の日時一覧（太陽黄経, 日時）を
    前年12月〜翌年2月まで広めに生成し、時系列にソートして返す。
    """
    from app.calculation.tables import MONTH_TERM_LONGITUDES

    years = [birth_dt_jst.year - 1, birth_dt_jst.year, birth_dt_jst.year + 1]
    entries: list[tuple[int, datetime]] = []
    for y in years:
        for lon in MONTH_TERM_LONGITUDES:
            entries.append((lon, find_term_datetime_jst(y, lon)))
    entries.sort(key=lambda e: e[1])
    return entries
