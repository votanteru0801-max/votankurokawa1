# 黒革の手帳

石橋輝一専用の人事分析LINE Bot。四柱推命・算命学の決定論的計算エンジンと、Googleスプレッドシートの人事情報、Claude APIによる人事的解釈を組み合わせ、人事判断を補助する「参謀」として回答します。

利用者は石橋輝一のみです。占術だけで採用・不採用・昇格・降格・異動・退職勧奨等を自動決定しません。

## クイックスタート（ローカル、認証情報なしで試す）

```bash
cp .env.example .env
docker compose up --build
```

別ターミナルで動作確認:
```bash
docker compose exec app python scripts/seed_mock_data.py
python scripts/mock_line_client.py --text "人物を登録"
```

サーバーログ（`docker compose logs -f app`）に、Botの応答が`[MOCK LINE REPLY ...]`として出力されます。`.env`の既定値では、LINE・Google Sheets・Anthropic APIすべてモックで動作するため、実際の認証情報は不要です。

## ドキュメント一覧

| ドキュメント | 内容 |
|---|---|
| [docs/requirements.md](docs/requirements.md) | 要件定義 |
| [docs/architecture.md](docs/architecture.md) | システム設計・処理フロー（Mermaid図） |
| [CLAUDE.md](CLAUDE.md) | AIコーディングツール向け開発ガイド |
| [docs/assumptions.md](docs/assumptions.md) | 開発にあたり置いた仮定 |
| [docs/INPUT_REQUIRED.md](docs/INPUT_REQUIRED.md) | 不足している認証情報・テストデータ |
| [docs/current-sheet-schema.md](docs/current-sheet-schema.md) | 既存スプレッドシート構成調査（未実施・調査手順あり） |
| [docs/data-dictionary.md](docs/data-dictionary.md) | データ項目定義 |
| [docs/calculation-policy.md](docs/calculation-policy.md) | 命式計算の流派・ルール・検証状況 |
| [docs/golden-test-guide.md](docs/golden-test-guide.md) | ゴールデンテストの追加・検証手順 |
| [docs/ai-prompt-design.md](docs/ai-prompt-design.md) | Claude連携設計・データ最小化・プロンプトインジェクション対策 |
| [docs/security.md](docs/security.md) | セキュリティ設計 |
| [docs/privacy-and-retention.md](docs/privacy-and-retention.md) | プライバシー・データ保持方針 |
| [docs/line-setup.md](docs/line-setup.md) | LINE公式アカウント・Messaging APIセットアップ |
| [docs/anthropic-setup.md](docs/anthropic-setup.md) | Anthropic Claude APIセットアップ |
| [docs/google-sheets-setup.md](docs/google-sheets-setup.md) | Google Sheets APIセットアップ |
| [docs/google-cloud-deployment.md](docs/google-cloud-deployment.md) | Google Cloudへの公開手順 |
| [docs/operations.md](docs/operations.md) | 運用手順 |
| [docs/backup-and-restore.md](docs/backup-and-restore.md) | バックアップ・復元 |
| [docs/troubleshooting.md](docs/troubleshooting.md) | トラブルシューティング |
| [docs/test-plan.md](docs/test-plan.md) | テスト計画・実行方法 |
| [docs/cost-estimate.md](docs/cost-estimate.md) | 月額費用概算 |
| [docs/phase2-design.md](docs/phase2-design.md) | 第2段階設計（相性分析・比較・チーム編成等） |
| [docs/phase3-design.md](docs/phase3-design.md) | 第3段階設計（将来対応） |

## 主なディレクトリ構成
```
app/            アプリケーション本体（FastAPI）
  calculation/    四柱推命・算命学の決定論的計算エンジン
  sheets/         Googleスプレッドシート連携（本番/モック切替可能）
  db/             PostgreSQLモデル
  ai/             Claude API連携・ツール定義・オーケストレーター
  services/       登録・更新・取り消し・面談記録等のアプリケーションロジック
  line/           LINE Webhook・メッセージ分割・リッチメニュー・自然文パーサー
  schemas/        人物情報スキーマ
tests/          自動テスト
golden_tests/   ゴールデンテストデータ・CLI
alembic/        DBマイグレーション
scripts/        運用・セットアップスクリプト
assets/         リッチメニュー画像・設定JSON
```

## 開発を始める前に
`CLAUDE.md`を必ず確認してください。命式計算はLLMに一切推測させないこと、書き込み操作は必ずアプリケーション層で検証・確認・監査ログを経ること等、本プロジェクトの安全設計上の絶対ルールが記載されています。
