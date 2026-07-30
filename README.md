# 命式相性ナビ LINE Bot

算命学・四柱推命の命式（干支・五行・十大主星／通変星・十二大従星／十二運・空亡）に基づき、
メンバーの相性やチーム編成、月初の傾向レポートをLINE上で確認できるBotです。

## できること（LINEでのメッセージ例）

| やりたいこと | 送るメッセージ例 |
|---|---|
| 個人の命式・傾向分析 | `山田太郎` |
| 2人の相性診断 | `山田太郎 佐藤花子` |
| 新規プロジェクトのチーム編成分析（3名以上） | `山田太郎 佐藤花子 鈴木一郎` |
| 面談メモの追加 | `メモ 山田太郎 最近新しい提案に積極的` |
| 今月のレポート | `月次レポート` |

毎月1日 9:00（JST）には、空亡の時期にあたるメンバーの一覧を自動でLINEに配信します（設定した場合）。

## 1. LINE公式アカウントの準備

1. [LINE Developers](https://developers.line.biz/) にログインし、プロバイダーを作成
2. 「Messaging API」チャネルを新規作成
3. チャネル基本設定から **チャネルシークレット** を取得
4. Messaging API設定から **チャネルアクセストークン（長期）** を発行
5. 応答メッセージ・あいさつメッセージは「無効」に、Webhookは「有効」にしておく

## 2. ローカルでの動作確認

```bash
cd linebot
cp .env.example .env
# .env に LINE_CHANNEL_ACCESS_TOKEN と LINE_CHANNEL_SECRET を記入
npm install
npm start
```

ローカルで試す場合は [ngrok](https://ngrok.com/) 等でトンネルを張り、
発行されたURL＋`/webhook` をLINE DevelopersのWebhook URLに設定してください。

## 3. 本番デプロイ（Render の例）

1. このフォルダ一式をGitHubリポジトリにpush（`.env`は含めない）
2. [Render](https://render.com/) で「New Web Service」→ 対象リポジトリを選択
3. Build Command: `npm install` / Start Command: `npm start`
4. Environment タブで以下を設定
   - `LINE_CHANNEL_ACCESS_TOKEN`
   - `LINE_CHANNEL_SECRET`
   - `LINE_PUSH_TARGET`（月初自動配信を使う場合。グループID/ユーザーIDの調べ方は下記）
5. デプロイ完了後に発行されるURL（例：`https://xxxx.onrender.com`）＋ `/webhook` を
   LINE DevelopersのWebhook URLに設定し、「検証」で成功することを確認
6. Botを友だち追加、または社内のLINEグループに招待すれば利用開始

### LINE_PUSH_TARGET（配信先ID）の調べ方
Webhookのイベントログに `event.source.groupId` または `event.source.userId` が出力されるので、
一度Botにメッセージを送信/グループに招待した状態でログを確認し、該当IDを設定してください。

## 4. データの保存について

現状は `members.json` に直接保存するシンプルな構成です（サーバー再起動でも消えません）。
メンバー数や更新頻度が増えてきた場合は、Render等の永続ディスクの利用、またはSupabase/PlanetScale等の
外部データベースへの移行を推奨します（ご希望があれば移行版も作成します）。

## 5. 精度に関する注意

- 干支（年柱・月柱・日柱）の算出は標準的な暦計算に基づいています
- 月柱の節入り日・大運の開始年齢は簡易計算（概算の節入り日を使用）のため、実際とは前後1日〜1年程度ずれる場合があります
- 算命学の十大主星・十二大従星は、四柱推命の通変星・十二運と同一の算出方法に基づく名称違いとして実装しています
- すべて対話のきっかけ・参考情報であり、人事評価や配置の断定的な根拠として使用しないでください
