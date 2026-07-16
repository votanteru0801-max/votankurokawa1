# 運用手順

## 1. 日常運用
- 石橋輝一がLINEで通常通り利用するだけで、追加の運用作業は基本的に発生しません。
- リッチメニューの6項目、または自然文での問いかけで操作します。

## 2. ログ確認
- ローカル: `docker compose logs -f app`
- 本番: `gcloud run services logs read kuroeda-techo --region asia-northeast1`

## 3. エラー発生時の一次対応
1. LINEに表示されたエラーメッセージを確認する（内部詳細は表示されない設計）。
2. `error_log`テーブル（PostgreSQL）で詳細を確認する:
```sql
SELECT occurred_at, component, error_type, message FROM error_log ORDER BY occurred_at DESC LIMIT 20;
```
3. `docs/troubleshooting.md`の該当項目を参照する。

## 4. バージョンアップ手順
```bash
git pull
docker compose build app
docker compose run --rm app alembic upgrade head
docker compose up -d
```
本番（Cloud Run）の場合は`docs/google-cloud-deployment.md`の手順4〜6を再実行します。

## 5. 依存関係の更新
```bash
pip list --outdated
pip install -U <パッケージ名>
# requirements.txt / requirements-dev.txt を更新後、pytestで回帰確認
```

## 6. 計算ポリシー変更時の手順
1. `app/calculation/policy.py`の該当設定を変更する。
2. `docs/calculation-policy.md`を更新する。
3. `python -m golden_tests.cli run`で既存ゴールデンテストへの影響を確認する。
4. `pytest tests/test_calculation_golden.py`で回帰確認する。

## 7. リッチメニュー更新
```bash
docker compose exec app python scripts/generate_rich_menu_image.py
docker compose exec app python scripts/register_rich_menu.py
```

## 8. 月次確認事項（推奨）
- Anthropic API・LINE公式アカウント・Google Cloudの利用料金確認（`docs/cost-estimate.md`）。
- `pip-audit`による依存関係脆弱性チェック（`docs/security.md`）。
- ゴールデンテストデータの追加・更新状況確認。
