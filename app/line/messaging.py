"""LINEメッセージの分割送信ユーティリティ。
1通あたりの文字数・1回あたりの送信数上限は app/config.py の LineLimits で管理する。
"""
from __future__ import annotations

from app.config import LineLimits


def split_message(text: str, chunk_length: int = LineLimits.SAFE_CHUNK_LENGTH) -> list[str]:
    """意味のある単位（見出し"■"や空行）でなるべく分割し、上限文字数を超えないようにする。"""
    if len(text) <= chunk_length:
        return [text]

    blocks = text.split("\n\n")
    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= chunk_length:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(block) <= chunk_length:
                current = block
            else:
                # ブロック自体が長すぎる場合は強制的に文字数で分割する
                for i in range(0, len(block), chunk_length):
                    chunks.append(block[i : i + chunk_length])
                current = ""
    if current:
        chunks.append(current)
    return chunks


def prepare_reply_messages(text: str) -> list[str]:
    """LINEの1回あたり最大送信数に収まるようメッセージを準備する。
    超過する場合は、末尾に省略の注記を追加する。
    """
    chunks = split_message(text)
    if len(chunks) > LineLimits.MAX_MESSAGES_PER_REPLY:
        chunks = chunks[: LineLimits.MAX_MESSAGES_PER_REPLY - 1]
        chunks.append("（回答が長いため一部省略しました。詳細は改めてご質問ください。）")
    return chunks
