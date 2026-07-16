#!/usr/bin/env python3
"""LINEにリッチメニューを登録する（LINE_MODE=live、本番チャネル設定後に実行）。
事前に scripts/generate_rich_menu_image.py で画像を生成しておくこと。
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.line.rich_menu import register_rich_menu

IMAGE_PATH = Path(__file__).resolve().parent.parent / "assets" / "rich_menu.png"


def main() -> None:
    if not IMAGE_PATH.exists():
        print(f"画像が見つかりません: {IMAGE_PATH}\n先に python scripts/generate_rich_menu_image.py を実行してください。", file=sys.stderr)
        sys.exit(1)
    rich_menu_id = register_rich_menu(str(IMAGE_PATH))
    print(f"リッチメニューを登録しました。richMenuId: {rich_menu_id}")


if __name__ == "__main__":
    main()
