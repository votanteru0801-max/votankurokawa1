# Google Cloudへの公開手順（Cloud Run + Cloud SQL）

**重要: 本番リソースの作成・本番デプロイは、石橋輝一の明示的な承認を得てから実施してください。** 以下は承認後に実施する手順です。

最終確認: 2026-07-16。

## 1. 事前準備
```bash
# Google Cloud CLIのインストール（未導入の場合）
# https://cloud.google.com/sdk/docs/install の手順に従う

gcloud auth login
gcloud config set project <あなたのプロジェクトID>
gcloud services enable run.googleapis.com sqladmin.googleapis.com secretmanager.googleapis.com \
  cloudtasks.googleapis.com sheets.googleapis.com
```

## 2. Cloud SQL for PostgreSQLの作成
```bash
gcloud sql instances create kuroeda-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=asia-northeast1 \
  --storage-size=10GB

gcloud sql databases create kuroeda --instance=kuroeda-db
gcloud sql users create kuroeda --instance=kuroeda-db --password=<強力なパスワード>
```
インスタンスサイズ（`db-f1-micro`）は石橋輝一1名利用という前提の初期案です。負荷状況に応じて調整してください。

## 3. Secret Managerへのシークレット登録
```bash
echo -n "<LINE_CHANNEL_SECRET>" | gcloud secrets create line-channel-secret --data-file=-
echo -n "<LINE_CHANNEL_ACCESS_TOKEN>" | gcloud secrets create line-channel-access-token --data-file=-
echo -n "<ANTHROPIC_API_KEY>" | gcloud secrets create anthropic-api-key --data-file=-
gcloud secrets create google-service-account --data-file=/path/to/service-account.json
```

## 4. コンテナイメージのビルド・登録
```bash
gcloud builds submit --tag asia-northeast1-docker.pkg.dev/<プロジェクトID>/kuroeda/app:latest
```
（事前にArtifact Registryリポジトリ`kuroeda`の作成が必要です: `gcloud artifacts repositories create kuroeda --repository-format=docker --location=asia-northeast1`）

## 5. Cloud Runへのデプロイ
```bash
gcloud run deploy kuroeda-techo \
  --image asia-northeast1-docker.pkg.dev/<プロジェクトID>/kuroeda/app:latest \
  --region asia-northeast1 \
  --platform managed \
  --add-cloudsql-instances <プロジェクトID>:asia-northeast1:kuroeda-db \
  --set-env-vars APP_ENV=production,LINE_MODE=live,GOOGLE_SHEETS_MODE=live,ANTHROPIC_MODE=live,ALLOWED_LINE_USER_ID=<石橋輝一のLINEユーザーID>,ANTHROPIC_MODEL=<モデルID>,HR_SPREADSHEET_ID=14Qz4S4s3CGOrjFsijOvjXy542BkG3DJ3gLYzZFAXWvg \
  --set-secrets LINE_CHANNEL_SECRET=line-channel-secret:latest,LINE_CHANNEL_ACCESS_TOKEN=line-channel-access-token:latest,ANTHROPIC_API_KEY=anthropic-api-key:latest,GOOGLE_APPLICATION_CREDENTIALS=/secrets/google-service-account.json \
  --allow-unauthenticated
```
`--allow-unauthenticated`はLINE Webhookを受信するために必要です（署名検証はアプリ側で実施）。

## 6. マイグレーション適用
Cloud SQL Auth Proxy等を使い、本番DBに対して`alembic upgrade head`を実行してください。
```bash
cloud-sql-proxy <プロジェクトID>:asia-northeast1:kuroeda-db &
DATABASE_URL=postgresql+psycopg://kuroeda:<パスワード>@127.0.0.1:5432/kuroeda alembic upgrade head
```

## 7. Webhook URLの設定
デプロイ後に表示されるCloud RunのURL（例: `https://kuroeda-techo-xxxxx.a.run.app`）に`/webhook`を付与し、LINE Developersコンソールに設定します（`docs/line-setup.md`）。

## 8. ログ確認
```bash
gcloud run services logs read kuroeda-techo --region asia-northeast1 --limit 100
```
または Cloud Loggingコンソールで`resource.type="cloud_run_revision"`をフィルタして確認できます。

## 9. Cloud Tasks（非同期処理の本番実装、必要に応じて）
MVPではCloud Run内の`BackgroundTasks`で非同期処理を行っていますが、負荷増加時はCloud Tasksへの移行を検討してください。`app/line/webhook.py`の`process_event`をCloud Tasksのハンドラエンドポイントとして切り出す構成に変更します。
