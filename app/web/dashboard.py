"""石橋輝一専用の簡易Webダッシュボード（/dashboard）。

LINE版と同じデータ（Googleスプレッドシート）・同じAIクライアントを使い、
「一覧を見ながら選ぶ」操作がしやすい機能をタブ形式のWeb画面として提供する。
- 社員一覧タブ: 氏名・所属・役職・MBTIのみで検索・一覧表示（機微情報は表示しない）。
  各行から簡易/詳細分析をLINEと同じロジックで実行できる。
- メンバー選定タブ: 条件を入力して新プロジェクトメンバー候補をAIに推薦させる
- 今月のアラートタブ: 命式の十二運（伝統的な命理学の法則）から機械的に
  気力が下がりやすい時期の人物を抽出する。AIは使わない（無料枠のトークン
  上限に左右されず、全社員分でも安定して動く設計）。

認証は簡易パスワードのみ（単一利用者向けの最小構成）。DASHBOARD_PASSWORD が
未設定の場合はダッシュボード自体を無効化し、機微な人事情報が無防備に
公開される事故を防ぐ。
"""
from __future__ import annotations

import hashlib
import hmac

from fastapi import APIRouter, Cookie, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.ai.client_interface import AnalysisGenerationError
from app.config import get_settings
from app.db.base import get_engine
from app.services import audit_service
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard")

COOKIE_NAME = "kuroeda_dashboard_session"


def _session_token(password: str) -> str:
    # パスワードそのものをCookieに入れず、固定ソルトとのHMACに変換して保存する。
    return hmac.new(password.encode("utf-8"), b"kuroeda-dashboard-session-v1", hashlib.sha256).hexdigest()


def _is_authenticated(session_cookie: str | None) -> bool:
    settings = get_settings()
    if not settings.dashboard_password or not session_cookie:
        return False
    return hmac.compare_digest(session_cookie, _session_token(settings.dashboard_password))


def _require_auth(session_cookie: str | None) -> None:
    if not _is_authenticated(session_cookie):
        raise HTTPException(status_code=401, detail="認証が必要です。/dashboard/ からログインしてください。")


LOGIN_HTML = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>黒革の手帳 - ログイン</title>
<style>
  body {{ font-family: sans-serif; background: #f4f2ee; display: flex; align-items: center;
         justify-content: center; height: 100vh; margin: 0; }}
  .box {{ background: #fff; padding: 32px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,.1); width: 320px; }}
  h1 {{ font-size: 18px; margin: 0 0 16px; }}
  input {{ width: 100%; box-sizing: border-box; padding: 8px; margin-bottom: 12px; border: 1px solid #ccc; border-radius: 4px; }}
  button {{ width: 100%; padding: 10px; background: #333; color: #fff; border: none; border-radius: 4px; cursor: pointer; }}
  .error {{ color: #c0392b; font-size: 13px; margin-bottom: 12px; }}
</style>
</head>
<body>
  <div class="box">
    <h1>黒革の手帳（Web版）</h1>
    {error_html}
    <form method="post" action="/dashboard/login">
      <input type="password" name="password" placeholder="パスワード" autofocus required>
      <button type="submit">ログイン</button>
    </form>
  </div>
</body>
</html>
"""

DASHBOARD_HTML = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>黒革の手帳 - ダッシュボード</title>
<style>
  body { font-family: sans-serif; background: #f4f2ee; margin: 0; color: #222; }
  header { background: #222; color: #fff; padding: 14px 20px; display: flex; justify-content: space-between; align-items: center; }
  header a { color: #ccc; font-size: 13px; text-decoration: none; }
  .tabs { display: flex; border-bottom: 1px solid #ccc; background: #fff; }
  .tab { padding: 12px 20px; cursor: pointer; font-size: 14px; color: #666; border-bottom: 3px solid transparent; }
  .tab.active { color: #222; font-weight: bold; border-bottom-color: #333; }
  .panel { display: none; padding: 20px; max-width: 900px; margin: 0 auto; }
  .panel.active { display: block; }
  input[type=text], textarea { width: 100%; box-sizing: border-box; padding: 8px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; }
  textarea { min-height: 70px; font-family: inherit; }
  button.action { margin-top: 10px; padding: 10px 18px; background: #333; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
  table { width: 100%; border-collapse: collapse; margin-top: 14px; background: #fff; }
  th, td { text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; font-size: 13px; }
  th { background: #fafafa; }
  .card { background: #fff; border-radius: 6px; padding: 14px 16px; margin-top: 14px; box-shadow: 0 1px 3px rgba(0,0,0,.06); }
  .card h3 { margin: 0 0 6px; font-size: 15px; }
  .caveats { background: #fff8e1; border: 1px solid #ffe0a3; border-radius: 6px; padding: 12px 14px; margin-top: 16px; font-size: 13px; }
  .muted { color: #888; font-size: 13px; }
  .loading { color: #888; font-size: 13px; margin-top: 10px; }
  .analysis-btn { padding: 4px 10px; font-size: 12px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; margin-right: 4px; }
  .analysis-text { white-space: pre-wrap; font-size: 13px; line-height: 1.6; }
  .alert-stage { display: inline-block; padding: 2px 8px; border-radius: 10px; background: #ffe0a3; font-size: 12px; margin-left: 6px; }
  .modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,.45); display: none; align-items: center; justify-content: center; z-index: 1000; }
  .modal-overlay.open { display: flex; }
  .modal-box { background: #fff; border-radius: 8px; padding: 20px 24px; max-width: 640px; width: 90%; max-height: 80vh; overflow-y: auto; box-shadow: 0 4px 20px rgba(0,0,0,.2); }
  .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
  .modal-header h3 { margin: 0; font-size: 16px; }
  .modal-close { border: none; background: none; font-size: 22px; line-height: 1; cursor: pointer; color: #888; }
</style>
</head>
<body>
<header>
  <div>黒革の手帳（Web版）</div>
  <a href="/dashboard/logout">ログアウト</a>
</header>
<div class="tabs">
  <div class="tab active" data-tab="people">社員一覧</div>
  <div class="tab" data-tab="team">メンバー選定</div>
  <div class="tab" data-tab="alerts">今月のアラート</div>
</div>

<div class="panel active" id="panel-people">
  <input type="text" id="people-search" placeholder="氏名・所属・役職・MBTIで検索">
  <table id="people-table">
    <thead><tr><th>氏名</th><th>所属</th><th>役職</th><th>MBTI</th><th>在籍状況</th><th>分析</th></tr></thead>
    <tbody></tbody>
  </table>
  <div class="muted" id="people-count"></div>
</div>

<div class="modal-overlay" id="analysis-modal">
  <div class="modal-box">
    <div class="modal-header">
      <h3 id="modal-title"></h3>
      <button class="modal-close" id="modal-close">&times;</button>
    </div>
    <div id="modal-body"></div>
  </div>
</div>

<div class="panel" id="panel-team">
  <p class="muted">例:「リーダーシップと創造性がある人を3人」のように、条件と人数を入力してください。</p>
  <textarea id="team-criteria" placeholder="条件を入力（例: リーダーシップと創造性がある人を3人）"></textarea>
  <button class="action" id="team-submit">候補を推薦させる</button>
  <div class="loading" id="team-loading" style="display:none;">選定中です（2段階で絞り込むため、最大1〜2分ほどかかることがあります）…</div>
  <div id="team-result"></div>
</div>

<div class="panel" id="panel-alerts">
  <p class="muted">命式の十二運（古典命理学の法則）から、今月「気力が下がりやすい時期」とされる人を機械的に抽出します（AIは使いません）。</p>
  <button class="action" id="alerts-load">今月のアラートを表示</button>
  <div class="loading" id="alerts-loading" style="display:none;">計算中です…</div>
  <div id="alerts-result"></div>
</div>

<script>
document.querySelectorAll('.tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    document.getElementById('panel-' + tab.dataset.tab).classList.add('active');
  });
});

async function loadPeople(q) {
  const res = await fetch('/dashboard/api/people?q=' + encodeURIComponent(q || ''));
  if (!res.ok) { return; }
  const data = await res.json();
  const tbody = document.querySelector('#people-table tbody');
  tbody.innerHTML = '';
  data.people.forEach(p => {
    const tr = document.createElement('tr');
    tr.innerHTML = '<td>' + escapeHtml(p.name) + '</td><td>' + escapeHtml(p.department) +
      '</td><td>' + escapeHtml(p.position) + '</td><td>' + escapeHtml(p.mbti) +
      '</td><td>' + escapeHtml(p.status) + '</td><td></td>';
    const btnSimple = document.createElement('button');
    btnSimple.className = 'analysis-btn';
    btnSimple.textContent = '簡易分析';
    btnSimple.addEventListener('click', () => runAnalysis(p.name, 'simple'));
    const btnDetailed = document.createElement('button');
    btnDetailed.className = 'analysis-btn';
    btnDetailed.textContent = '詳細分析';
    btnDetailed.addEventListener('click', () => runAnalysis(p.name, 'detailed'));
    tr.lastElementChild.appendChild(btnSimple);
    tr.lastElementChild.appendChild(btnDetailed);
    tbody.appendChild(tr);
  });
  document.getElementById('people-count').textContent = data.people.length + '件表示中（最大300件）';
}

function openModal(title) {
  document.getElementById('modal-title').textContent = title;
  document.getElementById('modal-body').innerHTML =
    '<p class="loading" style="display:block;">分析中です（初回アクセス直後は最大1分ほどかかることがあります）…</p>';
  document.getElementById('analysis-modal').classList.add('open');
}

function closeModal() {
  document.getElementById('analysis-modal').classList.remove('open');
}

document.getElementById('modal-close').addEventListener('click', closeModal);
document.getElementById('analysis-modal').addEventListener('click', (e) => {
  if (e.target.id === 'analysis-modal') { closeModal(); }
});

async function runAnalysis(name, mode) {
  const label = mode === 'detailed' ? '詳細分析' : '簡易分析';
  // クリックした瞬間に必ずモーダルを開き、押した反応がすぐわかるようにする。
  openModal(name + '（' + label + '）');
  const bodyEl = document.getElementById('modal-body');
  try {
    const res = await fetch('/dashboard/api/analysis?name=' + encodeURIComponent(name) + '&mode=' + mode);
    const data = await res.json();
    if (data.error) {
      bodyEl.innerHTML = '<p style="color:#c0392b">' + escapeHtml(data.error) + '</p>';
      return;
    }
    bodyEl.innerHTML = '<div class="analysis-text">' + escapeHtml(data.text) + '</div>';
  } catch (e) {
    bodyEl.innerHTML = '<p style="color:#c0392b">通信エラーが発生しました。時間をおいて再度お試しください。</p>';
  }
}

function escapeHtml(s) {
  return (s || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

let searchTimer = null;
document.getElementById('people-search').addEventListener('input', (e) => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => loadPeople(e.target.value), 250);
});

document.getElementById('alerts-load').addEventListener('click', async () => {
  const resultEl = document.getElementById('alerts-result');
  const loadingEl = document.getElementById('alerts-loading');
  resultEl.innerHTML = '';
  loadingEl.style.display = 'block';
  try {
    const res = await fetch('/dashboard/api/monthly-alerts');
    const data = await res.json();
    loadingEl.style.display = 'none';
    if (!data.alerts || data.alerts.length === 0) {
      resultEl.innerHTML = '<p class="muted">' + escapeHtml(data.target_month || '') + ': 該当者はいませんでした。</p>';
      return;
    }
    let html = '<p class="muted">' + escapeHtml(data.target_month) + '</p>';
    data.alerts.forEach(a => {
      html += '<div class="card"><h3>' + escapeHtml(a.name) + '（' + escapeHtml(a.department) + '）' +
        '<span class="alert-stage">' + escapeHtml(a.twelve_stage) + '</span></h3>' +
        '<p>' + escapeHtml(a.note) + '</p></div>';
    });
    html += '<div class="caveats">' + escapeHtml(data.caveat) + '</div>';
    resultEl.innerHTML = html;
  } catch (e) {
    loadingEl.style.display = 'none';
    resultEl.innerHTML = '<p style="color:#c0392b">通信エラーが発生しました。時間をおいて再度お試しください。</p>';
  }
});

document.getElementById('team-submit').addEventListener('click', async () => {
  const criteria = document.getElementById('team-criteria').value.trim();
  if (!criteria) { return; }
  const resultEl = document.getElementById('team-result');
  const loadingEl = document.getElementById('team-loading');
  resultEl.innerHTML = '';
  loadingEl.style.display = 'block';
  try {
    const res = await fetch('/dashboard/api/team-recommendation', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({criteria}),
    });
    const data = await res.json();
    loadingEl.style.display = 'none';
    if (data.error) {
      resultEl.innerHTML = '<p style="color:#c0392b">' + escapeHtml(data.error) + '</p>';
      return;
    }
    let html = '';
    (data.recommended || []).forEach(c => {
      html += '<div class="card"><h3>' + escapeHtml(c.name) + '</h3><p>' + escapeHtml(c.reason) + '</p></div>';
    });
    if ((data.caveats || []).length) {
      html += '<div class="caveats"><strong>注意事項</strong><ul>' +
        data.caveats.map(c => '<li>' + escapeHtml(c) + '</li>').join('') + '</ul></div>';
    }
    resultEl.innerHTML = html || '<p class="muted">条件に合う候補が見つかりませんでした。</p>';
  } catch (e) {
    loadingEl.style.display = 'none';
    resultEl.innerHTML = '<p style="color:#c0392b">通信エラーが発生しました。時間をおいて再度お試しください。</p>';
  }
});

loadPeople('');
</script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
def dashboard_page(kuroeda_dashboard_session: str | None = Cookie(default=None)) -> HTMLResponse:
    settings = get_settings()
    if not settings.dashboard_password:
        return HTMLResponse(
            "<p>ダッシュボードのパスワードが設定されていないため、現在利用できません。"
            "管理者にDASHBOARD_PASSWORDの設定を依頼してください。</p>",
            status_code=503,
        )
    if not _is_authenticated(kuroeda_dashboard_session):
        return HTMLResponse(LOGIN_HTML.format(error_html=""))
    return HTMLResponse(DASHBOARD_HTML)


@router.post("/login")
def dashboard_login(password: str = Form(...)):
    settings = get_settings()
    if not settings.dashboard_password or not hmac.compare_digest(password, settings.dashboard_password):
        return HTMLResponse(
            LOGIN_HTML.format(error_html='<p class="error">パスワードが違います。</p>'),
            status_code=401,
        )
    resp = RedirectResponse(url="/dashboard/", status_code=303)
    resp.set_cookie(
        COOKIE_NAME,
        _session_token(password),
        httponly=True,
        max_age=60 * 60 * 24 * 30,
        samesite="lax",
    )
    return resp


@router.get("/logout")
def dashboard_logout():
    resp = RedirectResponse(url="/dashboard/", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    return resp


@router.get("/api/people")
def api_people(q: str = "", kuroeda_dashboard_session: str | None = Cookie(default=None)) -> dict:
    _require_auth(kuroeda_dashboard_session)
    from app.sheets.google_repository import get_person_repository

    repo = get_person_repository()
    people = repo.list_all()
    if q:
        qn = q.strip()
        people = [
            p for p in people
            if qn in p.name or qn in p.department or qn in p.position or qn in p.mbti
        ]
    return {
        "people": [
            {"name": p.name, "department": p.department, "position": p.position, "mbti": p.mbti, "status": p.status}
            for p in people[:300]
        ]
    }


class TeamRecommendRequest(BaseModel):
    criteria: str


@router.post("/api/team-recommendation")
def api_team_recommendation(
    body: TeamRecommendRequest, kuroeda_dashboard_session: str | None = Cookie(default=None)
) -> dict:
    _require_auth(kuroeda_dashboard_session)
    from app.ai.factory import get_ai_client
    from app.services.team_recommendation import recommend_team_two_stage
    from app.sheets.google_repository import get_person_repository

    settings = get_settings()
    repo = get_person_repository()
    ai_client = get_ai_client()
    try:
        resp = recommend_team_two_stage(repo, ai_client, body.criteria)
    except AnalysisGenerationError as e:
        return {"error": f"候補の選定に失敗しました。時間をおいて再度お試しください。（{e}）"}

    engine = get_engine()
    with Session(engine) as db:
        audit_service.log_ai_request(
            db,
            f"web:{settings.allowed_line_user_id}",
            intent="team_recommendation_web",
            tool_calls={"recommend_team": 2},
            data_sent_summary={"criteria": body.criteria},
            model=settings.anthropic_model,
        )

    return {
        "criteria": resp.criteria,
        "recommended": [{"name": c.name, "reason": c.reason} for c in resp.recommended],
        "caveats": resp.caveats,
    }


@router.get("/api/analysis")
def api_analysis(
    name: str, mode: str = "simple", kuroeda_dashboard_session: str | None = Cookie(default=None)
) -> dict:
    _require_auth(kuroeda_dashboard_session)
    from app.ai.factory import get_ai_client
    from app.services import analysis_service, person_service
    from app.sheets.google_repository import get_person_repository

    if mode not in ("simple", "detailed"):
        mode = "simple"

    settings = get_settings()
    repo = get_person_repository()
    person, candidates = person_service.resolve_person_by_name(repo, name)
    if person is None and candidates:
        return {"error": person_service.build_disambiguation_message(candidates)}
    if person is None:
        return {"error": f"「{name}」に該当する人物が見つかりませんでした。"}

    ai_client = get_ai_client()
    actor_id = f"web:{settings.allowed_line_user_id}"
    label = "詳細分析" if mode == "detailed" else "簡易分析"
    engine = get_engine()
    with Session(engine) as db:
        try:
            text = analysis_service.run_analysis_for_person(
                db, repo, ai_client, actor_id, person, f"{person.name}の{label}", mode
            )
        except analysis_service.AnalysisError as e:
            return {"error": str(e)}

    return {"text": text}


@router.get("/api/monthly-alerts")
def api_monthly_alerts(kuroeda_dashboard_session: str | None = Cookie(default=None)) -> dict:
    _require_auth(kuroeda_dashboard_session)
    from datetime import date

    from app.services import monthly_alert
    from app.sheets.google_repository import get_person_repository

    repo = get_person_repository()
    today = date.today()
    alerts = monthly_alert.build_monthly_alerts(repo, today)
    return {
        "target_month": f"{today.year}年{today.month}月",
        "alerts": alerts,
        "caveat": monthly_alert.CAVEAT,
    }
