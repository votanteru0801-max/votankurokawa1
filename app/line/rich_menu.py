"""リッチメニュー定義と登録処理。
6項目: 人物を登録 / 簡易分析 / 詳細分析 / 相性分析 / 面談を記録 / 人材を比較
各ボタンはメッセージアクションで固定文言を送信し、app/ai/orchestrator.py の
トップレベル意図判定（_handle_idle）でそのまま解釈される。
画像サイズは2500x1686（LINE推奨サイズ）、2行3列のグリッドを想定する。
"""
from __future__ import annotations

RICH_MENU_WIDTH = 2500
RICH_MENU_HEIGHT = 1686
COLS = 3
ROWS = 2
CELL_W = RICH_MENU_WIDTH // COLS
CELL_H = RICH_MENU_HEIGHT // ROWS

MENU_ITEMS = [
    {"label": "人物を登録", "text": "人物を登録"},
    {"label": "簡易分析", "text": "簡易分析"},
    {"label": "詳細分析", "text": "詳細分析"},
    {"label": "相性分析", "text": "相性分析"},
    {"label": "面談を記録", "text": "面談を記録"},
    {"label": "人材を比較", "text": "人材を比較"},
]


def build_rich_menu_config() -> dict:
    areas = []
    for i, item in enumerate(MENU_ITEMS):
        row, col = divmod(i, COLS)
        areas.append(
            {
                "bounds": {"x": col * CELL_W, "y": row * CELL_H, "width": CELL_W, "height": CELL_H},
                "action": {"type": "message", "label": item["label"], "text": item["text"]},
            }
        )
    return {
        "size": {"width": RICH_MENU_WIDTH, "height": RICH_MENU_HEIGHT},
        "selected": True,
        "name": "黒革の手帳メインメニュー",
        "chatBarText": "メニュー",
        "areas": areas,
    }


def register_rich_menu(image_path: str) -> str:
    """LINEにリッチメニューを登録し、全ユーザーの既定メニューとして設定する。
    LINE_MODE=liveでのみ実行可能。戻り値はrichMenuId。
    """
    from app.config import get_settings

    settings = get_settings()
    if settings.line_mode.value != "live":
        raise RuntimeError("LINE_MODE=liveの場合のみリッチメニューを登録できます。")

    from linebot.v3.messaging import ApiClient, Configuration, MessagingApi, MessagingApiBlob, RichMenuRequest

    configuration = Configuration(access_token=settings.line_channel_access_token)
    config_dict = build_rich_menu_config()

    with ApiClient(configuration) as api_client:
        api = MessagingApi(api_client)
        blob_api = MessagingApiBlob(api_client)
        rich_menu_id = api.create_rich_menu(RichMenuRequest.from_dict(config_dict)).rich_menu_id
        with open(image_path, "rb") as f:
            blob_api.set_rich_menu_image(rich_menu_id, body=f.read(), _headers={"Content-Type": "image/png"})
        api.set_default_rich_menu(rich_menu_id)
    return rich_menu_id
