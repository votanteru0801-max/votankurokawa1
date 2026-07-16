# Google Sheets APIセットアップ手順

最終確認: 2026-07-16。画面は変更される可能性があるため、実施時に https://console.cloud.google.com を確認してください。

## 1. Google Cloudプロジェクトを作成する
1. https://console.cloud.google.com にアクセスし、新規プロジェクトを作成します（例: `kuroeda-techo`）。

## 2. Google Sheets APIを有効化する
1. 「APIとサービス」→「ライブラリ」で「Google Sheets API」を検索し、「有効にする」をクリックします。

## 3. サービスアカウントを作成する
1. 「APIとサービス」→「認証情報」→「認証情報を作成」→「サービスアカウント」を選択します。
2. 名前（例: `kuroeda-techo-sheets`）を入力して作成します。
3. 作成したサービスアカウントの「キー」タブから「鍵を追加」→「JSON」を選択し、JSONファイルをダウンロードします。
4. ダウンロードしたファイルを安全な場所に保存し、`.env`の`GOOGLE_APPLICATION_CREDENTIALS`にファイルパスを設定します（**Gitには絶対にコミットしないでください**）。

## 4. 対象スプレッドシートへのアクセス権限を付与する
1. 対象スプレッドシート（ID: `14Qz4S4s3CGOrjFsijOvjXy542BkG3DJ3gLYzZFAXWvg`）をブラウザで開きます。
2. 右上の「共有」から、サービスアカウントのメールアドレス（JSONファイル内の`client_email`、例: `kuroeda-techo-sheets@<プロジェクトID>.iam.gserviceaccount.com`）を「編集者」として追加します。

## 5. 既存シート構成の調査
アクセス権限付与後、以下を実行すると現在のシート構成を自動調査できます。
```bash
docker compose exec app python scripts/inspect_sheet_schema.py --spreadsheet-id 14Qz4S4s3CGOrjFsijOvjXy542BkG3DJ3gLYzZFAXWvg > docs/current-sheet-schema.md
```
結果を確認し、`app/sheets/schema_mapping.py`のマッピングを実際の列名に合わせて調整してください（**既存列の削除・改名・並び替えは行わないでください**）。

## 6. GOOGLE_SHEETS_MODEの切り替え
`.env`の`GOOGLE_SHEETS_MODE`を`mock`から`live`に変更すると、実際のスプレッドシートを読み書きするようになります。切り替え前に`app/sheets/google_repository.py`の実装が実シート構成に合わせて完成していることを確認してください（現状は骨格のみ、`docs/INPUT_REQUIRED.md`参照）。

## 7. レート制限について
Google Sheets APIには1分あたりのリクエスト数制限があります（2026年7月時点で読み取り300回/分など）。頻繁なアクセスが必要な場合は`person_index_cache`テーブルを活用したキャッシュの利用を検討してください。最新の制限値は https://developers.google.com/workspace/sheets/api/limits を確認してください。
