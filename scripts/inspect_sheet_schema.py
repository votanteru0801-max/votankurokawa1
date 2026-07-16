#!/usr/bin/env python3
"""既存Googleスプレッドシートの構成を調査し、Markdownレポートを標準出力へ書き出す。

事前にGOOGLE_APPLICATION_CREDENTIALSを設定し、サービスアカウントに対象シートの
閲覧権限を付与しておくこと。書き込みは一切行わない（読み取り専用）。
"""
from __future__ import annotations

import argparse
import collections
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spreadsheet-id", required=True)
    args = parser.parse_args()

    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
    except ImportError:
        print(
            "google-api-python-client / google-auth がインストールされていません。"
            " requirements.txt をインストールしてください。",
            file=sys.stderr,
        )
        sys.exit(1)

    from app.config import get_settings

    settings = get_settings()
    credentials = service_account.Credentials.from_service_account_file(
        settings.google_application_credentials,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    service = build("sheets", "v4", credentials=credentials)
    meta = service.spreadsheets().get(spreadsheetId=args.spreadsheet_id).execute()

    print(f"# 既存スプレッドシート構成調査結果\n")
    print(f"スプレッドシートID: `{args.spreadsheet_id}`\n")

    for sheet in meta["sheets"]:
        title = sheet["properties"]["title"]
        print(f"## シート: {title}\n")
        rng = f"{title}!A1:ZZ"
        values = (
            service.spreadsheets().values().get(spreadsheetId=args.spreadsheet_id, range=rng).execute()
        ).get("values", [])
        if not values:
            print("(空)\n")
            continue
        header, *rows = values
        print(f"行数（ヘッダー除く）: {len(rows)}\n")
        print("| 列 | 空欄率 | 型推定 | サンプル値 |")
        print("|---|---|---|---|")
        for i, col_name in enumerate(header):
            col_values = [r[i] if i < len(r) else "" for r in rows]
            empty = sum(1 for v in col_values if not v.strip())
            empty_rate = f"{empty / len(col_values) * 100:.0f}%" if col_values else "n/a"
            non_empty = [v for v in col_values if v.strip()]
            type_guess = _guess_type(non_empty)
            sample = non_empty[0] if non_empty else ""
            print(f"| {col_name} | {empty_rate} | {type_guess} | {sample} |")

        if "氏名" in header:
            idx = header.index("氏名")
            names = [r[idx] for r in rows if idx < len(r) and r[idx].strip()]
            dup = [n for n, c in collections.Counter(names).items() if c > 1]
            if dup:
                print(f"\n**同姓同名の可能性**: {', '.join(dup)}\n")
        print()


def _guess_type(values: list[str]) -> str:
    if not values:
        return "unknown"
    import re

    if all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) or re.fullmatch(r"\d{4}/\d{1,2}/\d{1,2}", v) for v in values[:20]):
        return "date"
    if all(re.fullmatch(r"-?\d+(\.\d+)?", v) for v in values[:20]):
        return "number"
    if all(v in ("TRUE", "FALSE", "はい", "いいえ", "true", "false") for v in values[:20]):
        return "boolean"
    return "string"


if __name__ == "__main__":
    main()
