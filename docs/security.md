# セキュリティ設計

## 1. 認証・認可
- LINE Webhookは`X-Line-Signature`ヘッダーをチャネルシークレットでHMAC-SHA256検証する（`app/auth/line_auth.py`）。
- 許可された唯一のLINEユーザーID（`ALLOWED_LINE_USER_ID`）以外のメッセージは、命式計算・Sheets参照・AI呼び出しを一切行わず、定型文「このアカウントでは利用できません。」のみを返す。
- 未許可ユーザーには社員名・登録人数・機能一覧・エラー詳細を絶対に開示しない（`tests/test_auth.py`で検証）。

## 2. Webhookの二重処理防止
- 各WebhookイベントのID（`webhookEventId`）を`webhook_events`テーブルに記録し、同一IDの再処理をスキップする。

## 3. シークレット管理
- `.env`はGit管理外（`.gitignore`）。`.env.example`にプレースホルダーのみ記載。
- Google認証情報（サービスアカウントJSON）もGit管理外。
- 本番はGoogle Cloud Secret Managerでシークレットを管理し、Cloud Runの環境変数として注入する（`docs/google-cloud-deployment.md`）。
- APIキー・トークン等はログに出力しない（`app/services/audit_service.py`は要約情報のみ記録）。

## 4. 通信
- 本番はCloud Run標準のHTTPS終端を利用する。LINE Webhook URLは常にHTTPSを指定する。

## 5. 入力検証・インジェクション対策
- すべての書き込み系操作はPydanticスキーマで型検証し、`app/services/`のアプリケーション層で権限・対象人物・必須項目・重複・確認有無を検証してから実行する。
- SQLインジェクション対策: SQLAlchemyのORM/パラメータバインディングのみを使用し、生SQL文字列結合は行わない。
- プロンプトインジェクション対策: 面談記録等のフリーテキストは常に「データ」としてラベル付けし、指示として実行しない（`docs/ai-prompt-design.md`）。

## 6. ログ・監査
- 監査ログ（`change_history`）に、操作日時・操作ユーザー・対象者・操作種別・変更前後・LINE入力原文・確認有無・実行結果・取り消し期限・取り消し済みかを記録する。
- エラーログ（`error_log`）は内部用。スタックトレース・APIキー・シート構造・DB情報はLINEへ絶対に表示しない（`app/line/webhook.py`のエラーハンドリング参照）。

## 7. 削除・保持
- 削除は原則として論理削除（`retention.deletion_status`）とし、復元可能にする。
- 採用候補者・社員・外部関係者の保持期間ポリシーをデータモデルに保持する（`docs/privacy-and-retention.md`）。

## 8. 最小権限
- Googleサービスアカウントには対象スプレッドシートへの必要最小限の権限（編集者）のみ付与する。
- Cloud Runサービスアカウントは、Secret Manager・Cloud SQL・Cloud Tasksへの必要最小限のIAMロールのみ付与する（`docs/google-cloud-deployment.md`）。

## 9. バックアップ・復元
- `docs/backup-and-restore.md`を参照。

## 10. 依存関係の脆弱性チェック
- `pip-audit`（またはGitHub Dependabot等）を定期的に実行することを推奨する。CI導入は将来対応とし、当面は手動実行:
```bash
pip install pip-audit --break-system-packages
pip-audit -r requirements.txt
```
