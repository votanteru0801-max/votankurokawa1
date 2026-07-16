# LINE公式アカウント・Messaging API セットアップ手順

非エンジニア向けに、画面操作の手順を日本語で説明します。LINE Developersの画面は変更されることがあるため、実際の表示が本書と異なる場合は画面の指示に従ってください（最終確認: 2026-07-16）。

## 1. LINE公式アカウントを作成する
1. https://www.lycbiz.com/jp/service/line-official-account/ にアクセスし、LINE公式アカウントを新規作成します（「黒革の手帳」など任意の名前で作成してください）。
2. アカウント種別は個人利用でも問題ありません。

## 2. Messaging APIを有効化する
1. 作成したLINE公式アカウントの管理画面（LINE Official Account Manager）にログインします。
2. 「設定」→「Messaging API」を開き、「Messaging APIを利用する」を選択します。
3. これによりLINE Developersコンソール（https://developers.line.biz/console/ ）上にMessaging APIチャネルが自動作成されます。

## 3. チャネルシークレット・チャネルアクセストークンを取得する
1. LINE Developersコンソールにログインし、対象チャネルを開きます。
2. 「チャネル基本設定」タブの「チャネルシークレット」を控えます → `.env`の`LINE_CHANNEL_SECRET`に設定。
3. 「Messaging API設定」タブの「チャネルアクセストークン（長期）」を発行し、控えます → `.env`の`LINE_CHANNEL_ACCESS_TOKEN`に設定。

## 4. 自分（石橋輝一）のLINEユーザーIDを確認する
最も簡単な方法:
1. LINE Developersコンソールの対象チャネルの「チャネル基本設定」タブを開きます。
2. 「あなたのユーザーID」という項目に表示されているID（`U`から始まる32文字の英数字）を控えます。
3. `.env`の`ALLOWED_LINE_USER_ID`に設定します。

このIDが、本Botを利用できる唯一のユーザーとして扱われます。

## 5. Webhook URLを設定する
1. アプリを起動している状態で（ローカルの場合は後述のngrok等でHTTPS化した上で）、Messaging API設定タブの「Webhook URL」に以下を入力します。
   - ローカル検証: `https://<ngrokなどのトンネルURL>/webhook`
   - 本番（Cloud Run）: `https://<Cloud RunサービスURL>/webhook`
2. 「Webhookの利用」をオンにします。
3. 「検証」ボタンを押し、200が返ることを確認します（アプリが起動していないと失敗します）。
4. 「応答メッセージ」はオフにしておくことを推奨します（Bot自身の応答と競合するため）。

## 6. ローカル検証用にHTTPSトンネルを準備する（任意）
ローカルPCで動かしたアプリにLINEからWebhookを届けるには、HTTPSの外部URLが必要です。ngrokの例:
```bash
brew install ngrok   # または公式サイトからダウンロード
ngrok http 8080
```
表示された`https://xxxx.ngrok-free.app`を上記Webhook URLに設定します（末尾に`/webhook`を付与）。

## 7. リッチメニューを登録する
```bash
docker compose exec app python scripts/generate_rich_menu_image.py
docker compose exec app python scripts/export_rich_menu_json.py
docker compose exec app python scripts/register_rich_menu.py
```
`LINE_MODE=live`かつ有効な`LINE_CHANNEL_ACCESS_TOKEN`が設定されている場合のみ実行できます。

## 8. 動作確認
1. LINE公式アカウントを友だち追加します。
2. 石橋輝一のアカウントからメッセージを送信し、応答が返ることを確認します。
3. 別のLINEアカウントから送信した場合は「このアカウントでは利用できません。」とだけ返ることを確認します。

## 9. 現行のLINE Messaging API仕様に関する注意
- 1通あたりの最大文字数・1回のreply/pushで送れるメッセージ数等は変更される可能性があります。最新仕様は https://developers.line.biz/ja/docs/messaging-api/ を確認し、`app/config.py`の`LineLimits`を更新してください。
- line-bot-sdk（Python）は2026年7月時点でv3系（`linebot.v3`）が現行です。`requirements.txt`のバージョンは定期的に見直してください。
