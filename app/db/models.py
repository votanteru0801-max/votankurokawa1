"""このファイルは使われていません。

PostgreSQL(SQLAlchemy)からGoogle Firestoreへの移行に伴い、ここにあった
ORMモデル定義（WebhookEvent, ConversationState, ChangeHistory,
AIRequestLog, ErrorLog 等）は廃止した。Firestore側のコレクション定義・
ドキュメント形状は、各サービスモジュール内にコメントとして記載している:
- app/services/conversation_service.py（conversation_states コレクション）
- app/services/history_service.py（change_history コレクション）
- app/services/audit_service.py（ai_request_log / error_log コレクション）
- app/line/webhook.py（webhook_events コレクション）

なお PendingOperation / PersonIndexCache / CalculationCache の3テーブルは
移行前の時点で実際には未使用（コード内から一切参照されていなかった）だった
ため、Firestore側には移植していない。

このファイル自体は不要なので、余裕があれば削除して構わない
（`git rm app/db/models.py`）。
"""
from __future__ import annotations
