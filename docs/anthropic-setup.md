# Anthropic Claude API セットアップ手順

最終確認: 2026-07-16。画面・料金は変更される可能性があるため、実施時に https://console.anthropic.com と https://platform.claude.com/docs を確認してください。

## 1. アカウント作成・APIキー取得
1. https://console.anthropic.com にアクセスし、アカウントを作成（または既存アカウントでログイン）します。
2. 左メニューの「API Keys」から新規キーを発行します。
3. 発行されたキーを`.env`の`ANTHROPIC_API_KEY`に設定します（キーは一度しか表示されないため、必ず控えてください）。

## 2. 利用可能なモデル名を確認する
1. https://platform.claude.com/docs/en/about-claude/models/overview でモデル一覧・モデルIDを確認します。
2. `.env`の`ANTHROPIC_MODEL`に、利用したいモデルのID（例: `claude-sonnet-4-6`など、実際に提供されている正式なモデルID）を設定します。**モデル名はコードに一切ハードコードされていません**（`app/config.py`）。

## 3. 請求設定
1. Anthropicコンソールの「Billing」から支払い方法を登録し、利用上限（Spending limit）を設定することを推奨します。
2. 想定コストは`docs/cost-estimate.md`を参照してください。**有料利用の開始は石橋輝一の明示的な判断で行ってください。**

## 4. 動作確認（ローカル）
`.env`で`ANTHROPIC_MODE=live`に切り替え、`ANTHROPIC_API_KEY`・`ANTHROPIC_MODEL`を設定した状態でアプリを再起動すると、実際のClaude APIが呼び出されます。切り替え前は`ANTHROPIC_MODE=mock`のままで全機能を検証できます。

## 5. 構造化出力・ツール呼び出しについて
本アプリは「強制ツール呼び出し」（tool_choice指定）でClaudeに構造化データを提出させ、Pydanticで検証します（`docs/ai-prompt-design.md`参照）。Anthropic APIの仕様変更があった場合は https://platform.claude.com/docs/en/api/messages のtool_choiceに関する記載を確認し、`app/ai/real_client.py`を更新してください。
