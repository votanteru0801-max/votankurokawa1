# プライバシー・データ保持方針

## 1. データ最小化
Claude APIへは質問目的に応じて最小限の情報のみを送信する（詳細は`docs/ai-prompt-design.md`）。health_info（健康）・family_info（家族）は、どの分析目的であっても自動的には送信しない。

## 2. 機微情報タグ
面談記録には`sensitive_tags`（health/family/retirement_consultation/other_sensitive）を付与できる（`app/schemas/person.py`）。将来的にタグに応じたアクセス制御・表示制御を強化する余地を残している。

## 3. 不利益判断の禁止
健康・家族事情・退職相談等の情報を、採用・不採用・昇格・降格・異動・退職勧奨等の自動判断根拠に使用しない（要件23章）。Claudeのシステムプロンプトにも明記している。

## 4. データ保持期間ポリシー

| 人物区分 | 保持方針 |
|---|---|
| 採用候補者 | 選考終了から6か月後に削除（`retention_policy=candidate_6m_after_selection`） |
| 社員 | 退職後1年間保存（`retention_policy=employee_1y_after_resignation`） |
| 外部関係者（コンサルタント・取引先・講師・パートナー） | 手動削除（`retention_policy=manual`） |

MVP第1段階では`retention_policy` / `retention_start_date` / `scheduled_delete_at` / `legal_hold` / `deletion_status`をデータモデルに保持するのみで、自動削除の実行バッチは実装しない（第3段階、`docs/phase3-design.md`参照）。

## 5. 削除
- 通常削除は論理削除（`deletion_status=soft_deleted`）。復元可能。
- `legal_hold=true`の場合、自動削除処理（第3段階実装時）は対象から除外する設計とする。

## 6. データ保管場所の責務分離
- 人事情報の正本: Googleスプレッドシート（ユーザーのGoogleアカウント管理下）
- 会話状態・監査情報: PostgreSQL（Cloud SQL、東京リージョン想定）

## 7. 開示・利用者
本Botの利用者は石橋輝一のみ。第三者への情報開示は行わない。
