# データディクショナリ

## 1. Person（人物情報 / Googleスプレッドシート正本、`app/schemas/person.py`）

| フィールド | 型 | 説明 |
|---|---|---|
| person_id | UUID | 内部人物ID。氏名だけに依存せず本人特定に使う |
| name | string | 氏名 |
| kana | string | フリガナ |
| aliases | string[] | 旧姓・別名 |
| category | enum | employee/candidate/external_consultant/business_partner/instructor/partner/other |
| gender | enum | male/female/other/unknown |
| birth_date | date\|null | 生年月日 |
| birth_time | time\|null | 出生時間（不明な場合はnull） |
| birth_time_unknown | bool | 出生時間が不明かどうか |
| birth_prefecture | string | 出生都道府県 |
| birth_city | string | 出生市区町村 |
| department | string | 所属店舗・部署 |
| position | string | 現在の役職 |
| hire_date | date\|null | 入社日 |
| resignation_date | date\|null | 退職日 |
| status | string | 在籍・選考・取引状態（自由記述。区分ごとに意味が異なるため用語集を別途整備） |
| mbti | string | MBTI（主要分析には使用しない） |
| desired_career | string | 本人の希望キャリア |
| evaluations | Evaluation[] | 人事評価（期間・要約） |
| interview_notes | InterviewNote[] | 面談記録（追記型、上書きしない） |
| retirement_consultation_notes | string | 退職相談情報（機微） |
| health_info | string | 健康・体調情報（機微） |
| family_info | string | 家族事情（機微） |
| notes | string | 備考 |
| retention | RetentionInfo | データ保持ポリシー情報 |
| created_at / updated_at | datetime | 登録日時・更新日時 |
| sheet_row_ref | string | スプレッドシート上の行参照 |

### InterviewNote
| フィールド | 型 | 説明 |
|---|---|---|
| note_id | UUID | 面談記録ID |
| occurred_on | date | 面談日 |
| author_line_user_id | string | 記録者（実質的に石橋輝一固定） |
| content | string | 面談内容の原文。**プロンプトとしては解釈しない「データ」として扱う** |
| sensitive_tags | enum[] | health/family/retirement_consultation/other_sensitive |

### RetentionInfo
| フィールド | 型 | 説明 |
|---|---|---|
| retention_policy | string | candidate_6m_after_selection / employee_1y_after_resignation / manual 等 |
| retention_start_date | date\|null | 保持起算日 |
| scheduled_delete_at | date\|null | 削除予定日（自動削除の実行は第3段階） |
| legal_hold | bool | 法的ホールド（削除保留） |
| deletion_status | enum | active/pending_delete/soft_deleted |

## 2. PostgreSQLテーブル（`app/db/models.py`）

| テーブル | 用途 |
|---|---|
| webhook_events | LINE Webhookイベントの受信・処理履歴。`line_event_id`で二重処理防止 |
| conversation_states | LINEユーザーごとの会話状態（登録途中・確認待ち等） |
| pending_operations | 確認待ちの書き込み操作。`idempotency_key`で冪等性を担保 |
| change_history | 変更履歴。取り消し（undo）の基礎データ |
| person_index_cache | Sheetsからの検索用キャッシュ（正本ではない） |
| calculation_cache | 命式計算結果のキャッシュ |
| ai_request_log | Claude APIリクエストのメタデータ（機微情報の本文は含めない） |
| error_log | エラー記録（内部用。LINEには表示しない） |

## 3. 命式計算結果（`app/calculation/schemas.py`）

`CalculationResult` = `shichuu_suimei`（四柱推命側, `FourPillarsResult`) + `sanmeigaku`（算命学側, `SanmeigakuResult`) + `luck_cycles`（大運・年運・月運, `LuckCyclesResult`) + `metadata`（計算ルールバージョン・計算日時・入力データ・出生時間有無・精度注意）。詳細は各Pydanticモデルのフィールドコメントおよび`docs/calculation-policy.md`を参照。
