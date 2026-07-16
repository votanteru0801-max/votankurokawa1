# バックアップ・復元手順

## 1. バックアップ対象
| データ | 保存場所 | バックアップ方法 |
|---|---|---|
| 人事情報（正本） | Googleスプレッドシート | Google Driveのバージョン履歴（自動）+ 定期的な手動エクスポート推奨 |
| 会話状態・監査・キャッシュ | Cloud SQL for PostgreSQL | Cloud SQLの自動バックアップ機能 |

## 2. Googleスプレッドシートのバックアップ
1. スプレッドシートの「ファイル」→「版の履歴」→「版の履歴を表示」でいつでも過去の状態を確認・復元できます（Google Driveの標準機能）。
2. 重要な変更前には「ファイル」→「コピーを作成」で手動バックアップを取ることを推奨します。

## 3. Cloud SQLの自動バックアップ設定
```bash
gcloud sql instances patch kuroeda-db \
  --backup-start-time=03:00 \
  --enable-bin-log
```
東京時間の深夜3時に自動バックアップを取得する設定例です。

## 4. Cloud SQLの手動バックアップ
```bash
gcloud sql backups create --instance=kuroeda-db
```

## 5. 復元手順（Cloud SQL）
```bash
gcloud sql backups list --instance=kuroeda-db
gcloud sql backups restore <BACKUP_ID> --restore-instance=kuroeda-db
```
**復元は既存データを上書きします。実行前に必ず石橋輝一の確認を取ってください。**

## 6. ローカル環境でのバックアップ（開発用）
```bash
docker compose exec db pg_dump -U kuroeda kuroeda > backup_$(date +%Y%m%d).sql
```
復元:
```bash
docker compose exec -T db psql -U kuroeda kuroeda < backup_20260716.sql
```

## 7. 論理削除データの扱い
論理削除（`deletion_status=soft_deleted`）されたレコードはバックアップにもそのまま含まれます。誤操作からの復元は「直前の変更を取り消して」（undo機能、24時間以内）、または論理削除フィールドを手動で`active`に戻すことで対応できます。
