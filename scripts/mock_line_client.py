#!/usr/bin/env python3
"""起動中のアプリ（docker compose up）に対して、LINE Webhookイベントを
模擬送信するCLI。LINE_MODE=mock時の署名なしでの疎通確認、または
LINE_MODE=live時のLINE_CHANNEL_SECRETを使った署名付き送信の両方に対応する。

使い方:
    python scripts/mock_line_client.py --user U0000000000000000000000000000000 --text "人物を登録"
    python scripts/mock_line_client.py --url http://localhost:8080/webhook --text "簡易分析"
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import urllib.request


def build_event(user_id: str, text: str) -> dict:
    return {
        "events": [
            {
                "type": "message",
                "webhookEventId": f"mock-{os.urandom(6).hex()}",
                "source": {"type": "user", "userId": user_id},
                "message": {"type": "text", "text": text},
            }
        ]
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8080/webhook")
    parser.add_argument("--user", default=os.environ.get("ALLOWED_LINE_USER_ID", "U0000000000000000000000000000000"))
    parser.add_argument("--text", required=True)
    parser.add_argument("--channel-secret", default=os.environ.get("LINE_CHANNEL_SECRET", ""))
    args = parser.parse_args()

    body = json.dumps(build_event(args.user, args.text)).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if args.channel_secret:
        mac = hmac.new(args.channel_secret.encode("utf-8"), body, hashlib.sha256).digest()
        headers["X-Line-Signature"] = base64.b64encode(mac).decode("utf-8")

    req = urllib.request.Request(args.url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req) as resp:
        print(f"status={resp.status}")
        print(resp.read().decode("utf-8"))
    print("\n応答本文はサーバー側ログ（[MOCK LINE REPLY ...]）に出力されます。"
          " docker compose logs -f app で確認してください。")


if __name__ == "__main__":
    main()
