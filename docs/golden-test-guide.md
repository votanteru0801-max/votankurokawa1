# ゴールデンテストガイド

## 1. 目的と原則
過去のAI回答を正解として扱わない。suimei.starcrawler.net（四柱推命・陰陽五行側）、unkoi.com（算命学側）の実際の画面・出力結果（画像・テキスト）のみを正解データとする。未確認の項目は`status: unverified`のまま扱い、テストの合否判定には使わない（`golden_tests/cli.py run`は`unverified`項目を「比較スキップ」として表示するのみで失敗にしない）。

## 2. データ形式
`golden_tests/data/*.yaml`。スキーマは`golden_tests/schema.py`の`GoldenTestEntry`を参照。必須項目: name, gender, birth_date, birth_place, source, confirmed_on, status。

## 3. 新規追加の手順
```bash
python -m golden_tests.cli new --name <slug>
```
生成された雛形YAMLに、氏名・生年月日・出生時間・出生地・出典・確認日を記入し、元サイトのスクリーンショット等が確認できた項目のみ`expected_*`を埋める。すべて確認できたら`status: verified`に変更する。

## 4. 検証
```bash
python -m golden_tests.cli validate
```
必須項目の欠落等、フォーマット不備を検出する。

## 5. 実行・差分確認
```bash
python -m golden_tests.cli run             # 全件
python -m golden_tests.cli diff --name <slug>   # 1件のみ
```
`expected_*`が設定されている項目のみMATCH/DIFFを表示し、未設定（null）の項目は「未確認（比較スキップ）」と表示される。

## 6. 日柱起点の校正
四柱推命の日柱は連続する60干支サイクルのカウントであり、起点定数（`app/calculation/four_pillars.py`の`DAY_PILLAR_ANCHOR_INDEX`）が未検証のプレースホルダーになっている。元サイトで確定した日柱データが手に入ったら、以下で校正候補値を算出できる。
```bash
python -m golden_tests.cli calibrate --name <slug> --day-pillar 甲子
```
表示された推奨値を`DAY_PILLAR_ANCHOR_INDEX`に設定し、他の全ゴールデンテストで再検証すること（複数人のデータで一貫して一致することを確認するまでは`verified`にしない）。

## 7. 現在収録されているデータ（すべてunverified）
- `ishibashi_teruichi.yaml`: 石橋輝一（1991-08-01 11:52、福岡県、男性）。中心星候補=車騎星。現行エンジンの計算値と一致（ただし正式なゴールデンデータではない）。
- `hamasawa_hikari.yaml`: 濱澤ひかり（1996-12-24 05:46、女性）。日干候補=乙、中心星候補=龍高星。いずれも現行エンジンの計算値と一致。
- `shimokozono_yuna.yaml`: 下小薗優菜（2002-03-14 17:30、女性）。日干候補=辛、中心星候補=禄存星。いずれも現行エンジンの計算値と一致。

これらの一致は好ましい兆候だが、ユーザーの記憶による候補値であり元サイトの一次情報ではないため、`status: verified`への変更は元サイトのスクリーンショット等の確認後に行うこと。

## 8. CI/自動実行への組み込み（将来）
`pytest tests/test_calculation_golden.py`は現時点でユーザー記憶の候補値を参考値として用いた回帰テストとして機能する。正式なゴールデンデータが揃い次第、`golden_tests/data/*.yaml`のverified項目を読み込んで動的にテストケースを生成する仕組みへ拡張することを推奨する。
