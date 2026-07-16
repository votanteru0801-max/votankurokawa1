#!/usr/bin/env python3
"""モックGoogle Sheetsリポジトリのサンプルデータを表示する。
MockPersonRepositoryはプロセス起動のたびに固定のサンプル人物データを
インメモリで生成するため、永続化のための追加操作は不要。
本スクリプトは、現在利用可能なサンプル人物を確認する目的で使用する。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.sheets.mock_repository import MockPersonRepository


def main() -> None:
    repo = MockPersonRepository()
    print("モック人事データ（すべて架空のサンプル）:")
    for p in repo.list_all():
        print(f"- {p.name}（{p.category.value}, person_id={p.person_id}）")
    print("\nこれらの人物に対して、LINEで以下のようなメッセージを試せます:")
    print('  「サンプル 太郎の簡易分析をして」')
    print('  「サンプル 太郎の役職をマネージャーに変更して」')
    print('  「今日のサンプル 太郎との面談内容を記録して：意欲的だった」')


if __name__ == "__main__":
    main()
