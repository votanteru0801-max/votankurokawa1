#!/usr/bin/env python3
"""リッチメニュー設定JSON（LINE Messaging API仕様）をファイルへ書き出す。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.line.rich_menu import build_rich_menu_config

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "rich_menu.json"


def main() -> None:
    config = build_rich_menu_config()
    OUTPUT_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"リッチメニュー設定JSONを書き出しました: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
