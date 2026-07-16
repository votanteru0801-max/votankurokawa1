# 第3段階 設計（将来対応）

## 1. 退職リスクの仮説分析
`DataPurpose.RETENTION_RISK`は既にMVPで定義済み。第3段階では、大運・年運の変化点（十二運が「絶」「墓」等になる年、天中殺の年等）を検出する`app/calculation/change_indicators.py`を新設し、人事情報側の兆候（評価低下、面談記録のネガティブワード検出等）と組み合わせて「面談で確認した方がよい人物」の候補を抽出するロジックを追加する。要件23章の通り、退職を断定する表現は使用しない。

## 2. 自動削除の実行
`retention_policy` / `scheduled_delete_at` / `legal_hold`はMVPからデータモデルに存在する。第3段階では、Cloud Scheduler等から定期実行するバッチ（`scripts/run_retention_cleanup.py`想定）で、`scheduled_delete_at`を過ぎ`legal_hold=false`のレコードを論理削除し、通知を送る。実行前に必ず確認ステップ（例: 実行対象一覧を石橋輝一へ事前通知）を設ける設計とする。

## 3. 定期通知
- 大運切り替わり通知: 各人物の大運開始日が近づいたら通知する`scripts/notify_luck_cycle_change.py`（Cloud Scheduler + Cloud Tasks想定）。
- 面談時期通知: 一定期間面談記録がない人物を検出して通知する。
いずれもLINE Push Messageで石橋輝一へ送信する。

## 4. 高度な人事提案
第2段階のチーム編成・比較機能の結果を蓄積し、傾向分析（例: 特定の中心星の配置が多いチームの離職率等）を行う統計的な補助機能を検討する。ただし占術と統計的相関を混同しないよう、表示上も「事実」「傾向」「仮説」の分離を維持する。

## 5. 海外出生者対応
MVPは日本国内出生者のみを対象とする（タイムゾーン`Asia/Tokyo`固定、節入り計算も日本標準時基準）。海外出生者対応には以下が必要:
- 出生地のタイムゾーン・経度情報の追加取得
- 真太陽時補正の実装（`CalculationPolicy.true_solar_time_correction`は既に設定項目として用意済みだが、計算ロジックは未実装）
- 節入り計算のタイムゾーン非依存化（`app/calculation/solar_terms.py`は天文計算自体はUTC基準のため、出力タイムゾーンを可変にする改修で対応可能）

## 6. その他将来検討事項
- Cloud Tasksへの完全移行（現状はCloud Run内BackgroundTasks）
- `person_index_cache`を活用したGoogle Sheets APIレート制限対策の強化
- CI/CDパイプライン（GitHub Actions等）でのpytest・ruff・mypy自動実行
