# トラブルシューティング

## LINEに表示されるエラーメッセージと対処

| メッセージ | 想定原因 | 対処 |
|---|---|---|
| このアカウントでは利用できません。 | 許可外のLINEユーザーからのアクセス | 石橋輝一のアカウントか確認。誤って別アカウントで送っていないか確認 |
| 該当する人物が見つかりませんでした | 氏名の表記揺れ、未登録 | 正確な氏名を確認、または新規登録する |
| 同姓同名の可能性がある人物が複数見つかりました | 同姓同名データが存在 | 表示された候補から番号または特徴で選択する |
| 出生時間が未登録のため... | 出生時間未登録の人物への時柱依存分析 | 出生時間が判明次第、基本情報更新で追加する |
| 命式計算でエラーが発生しました | 生年月日未登録、対応範囲外の日付等 | 生年月日を確認・登録する。持続する場合は`error_log`を確認 |
| AI分析の生成に失敗しました。時間をおいて再度お試しください | Claude API接続エラー・レート制限・構造化出力検証失敗 | 数分待って再試行。`ANTHROPIC_MODE`/APIキー設定を確認 |
| 処理中にエラーが発生しました | 予期しない内部エラー | `error_log`テーブルとCloud Loggingを確認 |
| 取り消せる操作がありません | 取り消し期限切れ、対象操作なし | `UNDO_WINDOW_MINUTES`設定を確認 |
| 更新内容の確認待ちです（該当する応答がない場合） | 会話状態がリセットされている | 最初から操作をやり直す |

## Google Sheetsに接続できない場合
1. `GOOGLE_APPLICATION_CREDENTIALS`のパスが正しいか確認する。
2. サービスアカウントに対象スプレッドシートの編集権限が付与されているか確認する（`docs/google-sheets-setup.md`）。
3. Google Sheets APIが有効化されているか確認する（`gcloud services list --enabled`）。
4. レート制限（429エラー）の場合は、時間を空けて再試行する。

## LINE Webhookが届かない場合
1. LINE Developersコンソールの「Webhookの利用」がオンになっているか確認する。
2. Webhook URLがHTTPSで、`/webhook`まで正しく設定されているか確認する。
3. アプリが起動しているか（`docker compose ps`）確認する。
4. 「応答メッセージ」機能がオンのままだと競合するため、オフにする。

## 署名検証エラーで403が返る場合
1. `LINE_CHANNEL_SECRET`が正しいか確認する。
2. プロキシ等でリクエストボディが改変されていないか確認する（署名はボディのバイト列全体で計算される）。

## Claude APIエラー
1. `ANTHROPIC_API_KEY`が正しいか、有効期限が切れていないか確認する。
2. `ANTHROPIC_MODEL`に指定したモデルIDが現在提供されているか、https://platform.claude.com/docs/en/about-claude/models/overview で確認する。
3. 利用上限（Spending limit）に達していないか、Anthropicコンソールの「Billing」で確認する。

## データベース接続エラー
1. `DATABASE_URL`が正しいか確認する。
2. `docker compose ps`でdbコンテナが起動しているか確認する。
3. マイグレーションが最新か確認する: `docker compose exec app alembic current`

## テストが失敗する場合
1. `docker compose up -d db`でテスト用DBが起動しているか確認する。
2. `alembic upgrade head`でスキーマが最新か確認する。
3. `.env`の`TEST_DATABASE_URL`（任意）でテスト専用DBを分離することを推奨する。
