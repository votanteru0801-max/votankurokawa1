#!/usr/bin/env python3
"""リッチメニュー画像を生成する（黒基調・日本語ラベル）。
Pillowと、日本語が表示できるフォント（システムのNoto Sans CJK等）が必要。
フォントが見つからない場合はラベルなしの黒背景グリッド画像を出力し、
手動でのテキスト追加を促すメッセージを表示する。
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.line.rich_menu import CELL_H, CELL_W, COLS, MENU_ITEMS, RICH_MENU_HEIGHT, RICH_MENU_WIDTH

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "assets" / "rich_menu.png"

BG_COLOR = (17, 17, 17)  # ほぼ黒
ACCENT_COLOR = (201, 169, 106)  # 金/革を思わせるアクセント色
TEXT_COLOR = (240, 240, 240)
GRID_COLOR = (60, 60, 60)


def _find_japanese_font() -> str | None:
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    try:
        out = subprocess.run(["fc-match", "-f", "%{file}", "Noto Sans CJK JP"], capture_output=True, text=True, timeout=5)
        if out.returncode == 0 and out.stdout.strip():
            return out.stdout.strip()
    except Exception:
        pass
    return None


def main() -> None:
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillowがインストールされていません。 pip install Pillow --break-system-packages", file=sys.stderr)
        sys.exit(1)

    img = Image.new("RGB", (RICH_MENU_WIDTH, RICH_MENU_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_path = _find_japanese_font()
    font = None
    if font_path:
        font = ImageFont.truetype(font_path, 90)
    else:
        print(
            "日本語フォントが見つかりませんでした。ラベルなしのグリッド画像を出力します。"
            " Noto Sans CJK JP等をインストールした環境で再実行するか、"
            " 生成された画像に手動でラベルを追加してください。",
            file=sys.stderr,
        )

    for i, item in enumerate(MENU_ITEMS):
        row, col = divmod(i, COLS)
        x0, y0 = col * CELL_W, row * CELL_H
        x1, y1 = x0 + CELL_W, y0 + CELL_H
        draw.rectangle([x0, y0, x1, y1], outline=GRID_COLOR, width=4)
        if font:
            label = item["label"]
            bbox = draw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            tx = x0 + (CELL_W - tw) / 2
            ty = y0 + (CELL_H - th) / 2
            draw.text((tx, ty), label, font=font, fill=TEXT_COLOR)
            draw.rectangle([x0 + 20, y0 + 20, x0 + 100, y0 + 30], fill=ACCENT_COLOR)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUTPUT_PATH)
    print(f"リッチメニュー画像を生成しました: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
