#!/usr/bin/env python3
"""ゴールデンテストCLI。

python -m golden_tests.cli list
python -m golden_tests.cli new --name <slug>
python -m golden_tests.cli validate
python -m golden_tests.cli run
python -m golden_tests.cli diff --name <slug>
python -m golden_tests.cli calibrate --name <slug> --day-pillar 甲子
"""
from __future__ import annotations

import sys
from datetime import date, time
from pathlib import Path

import click
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.calculation.engine import run_full_calculation
from app.calculation.policy import DEFAULT_POLICY
from app.calculation.schemas import BirthInput, Gender
from app.calculation.tables import ganzhi_index
from golden_tests.schema import GoldenTestEntry

DATA_DIR = Path(__file__).resolve().parent / "data"

GENDER_MAP = {"male": Gender.MALE, "female": Gender.FEMALE, "other": Gender.OTHER}


def _load_entry(path: Path) -> GoldenTestEntry:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return GoldenTestEntry.from_dict(raw)


def _all_entries() -> list[tuple[Path, GoldenTestEntry]]:
    return [(p, _load_entry(p)) for p in sorted(DATA_DIR.glob("*.yaml"))]


def _compute(entry: GoldenTestEntry):
    bt = time.fromisoformat(entry.birth_time) if entry.birth_time else None
    birth = BirthInput(
        birth_date=date.fromisoformat(entry.birth_date),
        birth_time=bt,
        birth_time_unknown=bt is None,
        prefecture=entry.birth_place,
        gender=GENDER_MAP.get(entry.gender, Gender.UNKNOWN),
    )
    return run_full_calculation(birth, DEFAULT_POLICY)


@click.group()
def cli():
    """黒革の手帳 ゴールデンテストCLI"""


@cli.command("list")
def list_entries():
    for path, entry in _all_entries():
        click.echo(f"{path.stem}\t{entry.name}\tstatus={entry.status}")


@cli.command("new")
@click.option("--name", required=True, help="ファイル名（拡張子なし）に使うスラッグ")
def new_entry(name: str):
    template = {
        "name": "氏名を入力",
        "gender": "male|female|other",
        "birth_date": "YYYY-MM-DD",
        "birth_time": "HH:MM または null",
        "birth_place": "都道府県 市区町村",
        "source": "出典（元サイト名・スクリーンショット取得日等）",
        "confirmed_on": date.today().isoformat(),
        "status": "unverified",
        "expected_year_pillar": None,
        "expected_month_pillar": None,
        "expected_day_pillar": None,
        "expected_hour_pillar": None,
        "expected_day_master": None,
        "expected_five_elements": None,
        "expected_center_star": None,
        "expected_juudai_shusei": {},
        "expected_juuni_daijuusei": {},
        "expected_tenchuusatsu": [],
        "expected_major_luck_start": None,
        "expected_major_cycles": [],
        "notes": "",
    }
    path = DATA_DIR / f"{name}.yaml"
    if path.exists():
        raise click.ClickException(f"既に存在します: {path}")
    path.write_text(yaml.dump(template, allow_unicode=True, sort_keys=False), encoding="utf-8")
    click.echo(f"雛形を作成しました: {path}")


@cli.command("validate")
def validate():
    ok = True
    for path, entry in _all_entries():
        try:
            GoldenTestEntry.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")))
            click.echo(f"OK   {path.name}")
        except Exception as e:  # noqa: BLE001
            ok = False
            click.echo(f"NG   {path.name}: {e}")
    if not ok:
        sys.exit(1)


def _diff_for_entry(path: Path, entry: GoldenTestEntry) -> list[str]:
    lines = []
    try:
        result = _compute(entry)
    except Exception as e:  # noqa: BLE001
        return [f"[{entry.name}] 計算エラー: {e}"]

    fp = result.shichuu_suimei
    sm = result.sanmeigaku
    computed = {
        "year_pillar": fp.year_pillar.stem + fp.year_pillar.branch,
        "month_pillar": fp.month_pillar.stem + fp.month_pillar.branch,
        "day_pillar": fp.day_pillar.stem + fp.day_pillar.branch,
        "hour_pillar": (fp.hour_pillar.stem + fp.hour_pillar.branch) if fp.hour_pillar else None,
        "day_master": fp.day_master_stem,
        "center_star": sm.center_star,
        "tenchuusatsu": sm.tenchuusatsu,
    }
    expected = {
        "year_pillar": entry.expected_year_pillar,
        "month_pillar": entry.expected_month_pillar,
        "day_pillar": entry.expected_day_pillar,
        "hour_pillar": entry.expected_hour_pillar,
        "day_master": entry.expected_day_master,
        "center_star": entry.expected_center_star,
        "tenchuusatsu": entry.expected_tenchuusatsu or None,
    }
    lines.append(f"[{entry.name}] status={entry.status}")
    for key, exp in expected.items():
        comp = computed.get(key)
        if exp in (None, [], ""):
            lines.append(f"  {key}: 未確認（比較スキップ） 計算値={comp}")
            continue
        mark = "MATCH" if str(comp) == str(exp) else "DIFF "
        lines.append(f"  {key}: {mark} 期待値={exp} / 計算値={comp}")
    return lines


@cli.command("run")
@click.option("--name", default=None, help="特定のエントリのみ実行（省略時は全件）")
def run_tests(name: str | None):
    entries = _all_entries()
    if name:
        entries = [(p, e) for p, e in entries if p.stem == name]
        if not entries:
            raise click.ClickException(f"見つかりません: {name}")
    for path, entry in entries:
        for line in _diff_for_entry(path, entry):
            click.echo(line)
        click.echo("")


@cli.command("diff")
@click.option("--name", required=True)
def diff_one(name: str):
    path = DATA_DIR / f"{name}.yaml"
    if not path.exists():
        raise click.ClickException(f"見つかりません: {path}")
    entry = _load_entry(path)
    for line in _diff_for_entry(path, entry):
        click.echo(line)


@cli.command("calibrate")
@click.option("--name", required=True, help="対象エントリのスラッグ")
@click.option("--day-pillar", required=True, help="確定した日柱の干支（例: 甲子）")
def calibrate(name: str, day_pillar: str):
    """確定した日柱データから DAY_PILLAR_ANCHOR_INDEX の正しい値を逆算する。"""
    from app.calculation.four_pillars import DAY_PILLAR_ANCHOR_DATE, DAY_PILLAR_ANCHOR_INDEX
    from app.calculation.policy import DEFAULT_POLICY

    path = DATA_DIR / f"{name}.yaml"
    if not path.exists():
        raise click.ClickException(f"見つかりません: {path}")
    entry = _load_entry(path)

    stem, branch = day_pillar[0], day_pillar[1]
    target_index = ganzhi_index(stem, branch)

    birth_date = date.fromisoformat(entry.birth_date)
    effective_date = birth_date
    if DEFAULT_POLICY.day_boundary_hour == 23 and entry.birth_time:
        h = int(entry.birth_time.split(":")[0])
        if h == 23:
            from datetime import timedelta

            effective_date = birth_date + timedelta(days=1)

    ordinal_diff = effective_date.toordinal() - DAY_PILLAR_ANCHOR_DATE.toordinal()
    required_index = (target_index - ordinal_diff) % 60

    click.echo(f"現在の DAY_PILLAR_ANCHOR_INDEX = {DAY_PILLAR_ANCHOR_INDEX}")
    click.echo(f"{entry.name}（{entry.birth_date}）の日柱を {day_pillar} とするために必要な値 = {required_index}")
    if required_index == DAY_PILLAR_ANCHOR_INDEX:
        click.echo("→ 現在の設定で一致しています。校正は不要です。")
    else:
        click.echo(
            "→ app/calculation/four_pillars.py の DAY_PILLAR_ANCHOR_INDEX を"
            f" {required_index} に更新し、他のゴールデンテストでも再検証してください。"
        )


if __name__ == "__main__":
    cli()
