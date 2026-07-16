# 必要な認証情報・テストデータ一覧

開発を止めないため、以下が揃うまではモック環境（`*_MODE=mock`）で全機能を検証できる構成にしている。実運用・本番デプロイには以下が必須。

## 1. LINE
| 項目 | 用途 | 状態 |
|---|---|---|
| LINE公式アカウント | Bot本体 | 未確認 |
| Messaging APIチャネルシークレット (`LINE_CHANNEL_SECRET`) | Webhook署名検証 | 未取得 |
| チャネルアクセストークン (`LINE_CHANNEL_ACCESS_TOKEN`) | メッセージ送信 | 未取得 |
| 石橋輝一のLINEユーザーID (`ALLOWED_LINE_USER_ID`) | 唯一の許可ユーザー判定 | 未取得（取得方法は`docs/line-setup.md`） |
| リッチメニュー用画像 | UI | `scripts/generate_rich_menu_image.py`で自動生成するプレースホルダーで代替可 |

## 2. Anthropic (Claude API)
| 項目 | 用途 | 状態 |
|---|---|---|
| `ANTHROPIC_API_KEY` | Claude API呼び出し | 未取得 |
| `ANTHROPIC_MODEL` | 使用モデル名 | 未確定（`.env.example`にプレースホルダー） |

## 3. Google
| 項目 | 用途 | 状態 |
|---|---|---|
| GCPプロジェクト | Sheets API/Cloud Run等 | 未確認 |
| サービスアカウントJSON鍵 or OAuthクライアント | Sheets API認証 | 未取得 |
| 対象スプレッドシートへの編集権限付与 | 人事情報正本の読み書き | 未確認（シートID: `14Qz4S4s3CGOrjFsijOvjXy542BkG3DJ3gLYzZFAXWvg` はユーザー提供済み） |

## 4. PostgreSQL
| 項目 | 用途 | 状態 |
|---|---|---|
| ローカルDB | Docker Composeで自動起動、追加作業不要 | 対応済み |
| 本番 Cloud SQL接続情報 | 本番運用 | 未作成（本番リソース作成はユーザー確認後） |

## 5. ゴールデンテスト用の元データ（画像・サイト出力）
過去のAI回答は正解として使用しない。以下の元サイト画面・出力結果（スクリーンショット可）が必要。候補値は`golden_tests/data/`に`status: unverified`として雛形登録済み。

| 氏名 | 生年月日時 | 出生地 | 性別 | 必要な元データ |
|---|---|---|---|---|
| 石橋輝一 | 1991-08-01 11:52 | 福岡県 | 男性 | suimei.starcrawler.net と unkoi.com それぞれの出力結果（画像またはテキスト） |
| 濱澤ひかり | 1996-12-24 05:46 | (市区町村不明) | 女性 | 同上 |
| 下小薗優菜 | 2002-03-14 17:30 | (市区町村不明) | 女性 | 同上 |

不足している項目（出生市区町村など）も含め確認が必要。

## 6. 未確定の運用ポリシー（石橋輝一の判断が必要）
- Cloud Runのリージョン（既定案: `asia-northeast1` 東京）でよいか。
- Cloud SQLのインスタンスサイズ（既定案: 最小構成 `db-f1-micro`相当、1名利用のため）でよいか。
- 本番デプロイのタイミング（有料リソース作成を伴うため、明示的な承認が必要）。

## モックでの代替方法

上記が揃うまでは、以下のモックで全フローを試せる：
- `GOOGLE_SHEETS_MODE=mock` — `app/sheets/mock_repository.py` がメモリ上のサンプル人物データを提供
- `ANTHROPIC_MODE=mock` — `app/ai/mock_client.py` が固定パターンの応答を返す（意図解釈は簡易ルールベース）
- `LINE_MODE=mock` — `scripts/mock_line_client.py` でWebhookイベントをCLIから模擬送信

`docker compose up` するだけでこれら全てmockのまま起動する（`.env.example`の既定値）。
