# 第2段階 設計（実装は分離）

対象機能: 2名の相性分析 / 複数人比較 / チーム編成 / 採用候補者分析 / 外部コンサルタントとの窓口選定

## 1. 設計方針
MVP第1段階の構造（決定論的計算エンジン、データ最小化、確認フロー、監査ログ）を一切変更せず、以下のレイヤーに追加する形で実装する。

- `app/ai/tools.py`の`compare_people` / `analyze_team`ツール定義（雛形は既にMVPに用意済み）
- `app/ai/tool_executor.py`の該当分岐（現状は`not_implemented_phase2`を返すのみ）
- `app/schemas/phase2.py`（新設）: `CompatibilityResult`, `TeamComposition`, `ComparisonResult`等のPydanticモデル
- `app/services/compatibility_service.py`（新設）
- `app/services/team_service.py`（新設）

## 2. 相性分析（2名）
### データモデル案
```python
class CompatibilityResult(BaseModel):
    person_a_id: str
    person_b_id: str
    boss_subordinate_relationship: list[LabeledPoint]
    peer_relationship: list[LabeledPoint]
    role_division: list[LabeledPoint]
    decision_making_compatibility: list[LabeledPoint]
    communication_notes: list[LabeledPoint]
    friction_points: list[LabeledPoint]
    complementary_points: list[LabeledPoint]
    five_element_balance_comment: str
    who_should_lead: str
    who_should_stabilize: str
    mediator_type_needed: str | None
    management_recommendations: list[LabeledPoint]
```
### 計算ロジック
両者の`FourPillarsResult`・`SanmeigakuResult`を取得し、五行の相生・相剋関係、通変星・十二運の組み合わせから決定論的な特徴量（例: 五行バランスの補完度、日干同士の相生相剋）を計算するモジュール`app/calculation/compatibility.py`を新設する。Claudeはこの特徴量＋人事情報を材料に文章化・提案を行う（命式の推測はさせない、MVPと同じ原則）。

## 3. 複数人比較
### データモデル案
```python
class ComparisonResult(BaseModel):
    candidates: list[str]  # person_id
    per_candidate: dict[str, ComparisonCandidateDetail]
    fortune_only_first_choice: str
    fortune_only_reason: str
    overall_first_choice: str
    overall_choice_conditions: list[str]
    concerns: list[LabeledPoint]
    required_support_roles: list[str]
    team_composition_after: str
    facts_to_confirm_before_decision: list[str]
```
「命式だけで見た第一候補」と「人事情報を含めた第一候補」を明示的に分離するのが要件上の重要点であり、レスポンススキーマにも両方のフィールドを用意する。

## 4. チーム編成
複数人の五行バランス・十大主星の分布を集計し、偏りや補完関係を可視化する`app/calculation/team_analysis.py`を新設する。

## 5. 採用候補者分析・外部コンサルタント窓口選定
基本的には簡易/詳細分析のロジックを再利用しつつ、`DataPurpose.CANDIDATE_SCREENING`用のプロンプト調整と、選考プロセス特有の確認事項（内定可否は占術で自動決定しない旨の強調）を追加する。

## 6. リッチメニューとの接続
「相性分析」「人材を比較」ボタンは既にMVPの`app/ai/orchestrator.py`で受理され、「この機能は第2段階で実装予定です」という案内を返すよう実装済み。第2段階実装時は、この分岐を実際のフローに置き換えるだけでよい。

## 7. テスト方針
`tests/test_phase2_compatibility.py`, `tests/test_phase2_comparison.py`, `tests/test_phase2_team.py`（新設）で、MVPと同様にモックAIクライアント・モックリポジトリを用いたテストを追加する。
