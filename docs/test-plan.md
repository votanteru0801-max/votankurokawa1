# テスト計画

## 1. テスト構成

| ファイル | 対象 | DB(Postgres)必要 |
|---|---|---|
| `tests/test_auth.py` | 署名検証・許可ユーザー照合 | 不要 |
| `tests/test_line_parsers.py` | 自然文パーサー（登録・更新・取り消し） | 不要 |
| `tests/test_messaging.py` | LINEメッセージ分割 | 不要 |
| `tests/test_calculation_golden.py` | 命式計算エンジン・ゴールデンデータ照合 | 不要 |
| `tests/test_ai_data_minimization.py` | データ最小化・構造化出力・プロンプトインジェクション対策 | 一部必要（統合テスト1件） |
| `tests/test_webhook.py` | Webhookエンドポイント（署名・health） | 不要（イベント処理自体はbackground taskのため空イベントのみ検証） |
| `tests/test_registration.py` | 登録フロー全般 | 必要 |
| `tests/test_update_undo.py` | 更新・取り消し・論理削除・冪等性 | 必要 |

## 2. 実行方法
```bash
docker compose up -d db
docker compose exec app alembic upgrade head
docker compose exec app pytest
```
または、ローカルにPostgreSQLがある場合:
```bash
pip install -r requirements.txt -r requirements-dev.txt
export DATABASE_URL=postgresql+psycopg://kuroeda:kuroeda@localhost:5432/kuroeda_test
alembic upgrade head
pytest
```

## 3. 開発中に実施した検証について
本プロジェクトの開発環境にはインターネット接続がなく、`requirements.txt`記載の実パッケージ（FastAPI, SQLAlchemy, anthropic, line-bot-sdk, google-api-python-client, pytest等）をインストールできなかった。そのため、以下の方法で可能な範囲の検証を行った。

1. 全Pythonファイルの構文チェック（`ast.parse`によるシンタックスエラー検出）。
2. pydantic互換の最小限シム実装を用いた、命式計算エンジン・登録/更新/取り消しオーケストレーターの手動実行によるロジック検証（実際にオーケストレーターを通してLINE風の会話を再現し、想定どおりの応答・状態遷移・データ更新が行われることを確認した）。
3. `click`・`PyYAML`・`Pillow`は環境に存在したため、ゴールデンテストCLIとリッチメニュー画像生成は実際に実行して動作確認済み。
4. `pytest`自体は環境になかったため、`tests/`配下のテストコードは記述後に自動実行できていない。**Docker Compose環境（`docs/README.md`のセットアップ手順）で`pytest`を実行し、結果を確認することを強く推奨する。**

## 4. 既知の未検証領域
- `app/sheets/google_repository.py`: 実スプレッドシート未確認のため、行↔Personマッピングは骨格のみ（`NotImplementedError`）。`docs/current-sheet-schema.md`調査後に実装が必要。
- `app/ai/real_client.py`: Anthropic APIキー未設定のため、実際のtool_choice強制ツール呼び出し・リトライ動作は未実施。`ANTHROPIC_MODE=live`設定後の手動確認を推奨する。
- `app/line/rich_menu.py`の`register_rich_menu`: LINEチャネル未作成のため未実施。

## 5. 手動確認チェックリスト（Docker Compose起動後）
- [ ] `docker compose up`でアプリ・DBが起動する
- [ ] `python scripts/mock_line_client.py --text "人物を登録"`で登録フローが開始する
- [ ] `python scripts/mock_line_client.py --text "簡易分析"`で対象人物確認→分析が返る
- [ ] `pytest`が全件成功する
- [ ] `python -m golden_tests.cli run`が実行できる
