"""運用データ（会話状態・監査ログ・変更履歴等）の保存先クライアント。

以前はPostgreSQL(SQLAlchemy)を使っていたが、Google Cloudへの完全移行・
完全無料化のため、Google Firestore（Googleの無料枠があるNoSQL DB）に変更した。
Google Sheetsに保存されている人事データ本体とは別の、アプリ内部の運用データのみを扱う。

認証は次の優先順で決定する:
1. GOOGLE_SERVICE_ACCOUNT_JSON（サービスアカウントJSONの中身を環境変数にそのまま
   入れる方式。Render等、GCPネイティブな認証が使えない環境向け）
2. GOOGLE_APPLICATION_CREDENTIALS（サービスアカウントJSONファイルへのパス）
3. どちらも未設定の場合はApplication Default Credentials（ADC）を使う。
   Cloud Run上でサービスアカウントを紐付けている場合は、追加設定なしで
   自動的にそのサービスアカウントとして認証される。
"""
from __future__ import annotations

import json
from functools import lru_cache

from google.cloud import firestore

from app.config import get_settings


@lru_cache
def get_firestore_client() -> firestore.Client:
    settings = get_settings()

    if settings.google_service_account_json:
        from google.oauth2 import service_account

        info = json.loads(settings.google_service_account_json)
        credentials = service_account.Credentials.from_service_account_info(info)
        return firestore.Client(credentials=credentials, project=info.get("project_id"))

    if settings.google_application_credentials:
        from google.oauth2 import service_account

        credentials = service_account.Credentials.from_service_account_file(
            settings.google_application_credentials
        )
        return firestore.Client(credentials=credentials, project=credentials.project_id)

    # Cloud Run等、GCP環境で動いている場合はここに来る（ADCで自動認証）。
    # ローカルのFirestoreエミュレータ使用時など、プロジェクトIDを自動検出
    # できない環境ではGOOGLE_CLOUD_PROJECTで明示的に指定する。
    if settings.google_cloud_project:
        return firestore.Client(project=settings.google_cloud_project)
    return firestore.Client()
