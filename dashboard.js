const calc = require('./calculations');

function esc(s){ return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function renderDashboard(rawMembers, opts){
  opts = opts || {};
  const q = opts.q || '';
  const result = opts.result || null;
  const candidateName = opts.candidateName || '';
  const candidateBirth = opts.candidateBirth || '';
  const candidateResult = opts.candidateResult || null;

  const withMeishiki = rawMembers.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth) }));

  // 所属（店舗）ごとにグループ化
  const groups = {};
  withMeishiki.forEach(m => {
    const g = m.group || '未分類';
    if(!groups[g]) groups[g] = [];
    groups[g].push(m);
  });

  const groupSections = Object.keys(groups).sort().map(g => {
    const rows = groups[g].map(m => `<tr>
      <td><a href="/?q=${encodeURIComponent(m.name)}">${esc(m.name)}</a></td>
      <td>${calc.pillarStr(m.meishiki.year)} ${calc.pillarStr(m.meishiki.month)} ${calc.pillarStr(m.meishiki.day)}</td>
      <td><span class="tag">${calc.KAN[m.meishiki.day.kanIdx]}（${calc.gogyoOf(m.meishiki.day.kanIdx)}）</span></td>
    </tr>`).join('');
    return `<div class="store-card">
      <h3>${esc(g)}（${groups[g].length}名）</h3>
      <table>
        <thead><tr><th>氏名</th><th>年柱／月柱／日柱</th><th>日主</th></tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  }).join('');

  const today = new Date();
  const curBranch = calc.monthBranch(today.getFullYear(), today.getMonth()+1, today.getDate());
  const kuubouList = withMeishiki.filter(m => calc.kuubouBranches(m.meishiki.dayIdx60).map(i=>calc.SHI[i]).includes(curBranch));
  const kuubouItems = kuubouList.map(m => `<li><a href="/?q=${encodeURIComponent(m.name)}">${esc(m.name)}（${esc(m.group)}）</a></li>`).join('');

  return `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>命式相性ナビ</title>
<style>
  :root{ --paper:#F6F1E6; --paper-deep:#EFE7D6; --ink:#20263B; --ink-soft:#5A5F72; --line:#D8CDB4; --accent:#8A2F2A; }
  *{box-sizing:border-box;}
  body{ margin:0; background:var(--paper); color:var(--ink); font-family:"Hiragino Kaku Gothic ProN",sans-serif; line-height:1.7; padding:0 0 60px; }
  header{ padding:32px 24px 20px; border-bottom:1px solid var(--line); text-align:center; }
  header .eyebrow{ letter-spacing:0.3em; font-size:11px; color:var(--ink-soft); margin-bottom:8px; }
  header h1{ font-family:"Hiragino Mincho ProN",serif; font-size:24px; margin:0; }
  main{ max-width:1000px; margin:0 auto; padding:28px 20px; }
  section{ margin-bottom:40px; }
  h2{ font-size:14px; letter-spacing:0.1em; color:var(--ink-soft); border-bottom:1px solid var(--line); padding-bottom:8px; margin-bottom:16px; }
  table{ width:100%; border-collapse:collapse; font-size:13px; background:#FFFDF8; }
  th,td{ text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); }
  th{ color:var(--ink-soft); font-size:11px; }
  a{ color:var(--ink); }
  .tag{ background:var(--paper-deep); padding:2px 8px; border:1px solid var(--line); font-size:11px; }
  .store-grid{ display:grid; grid-template-columns:repeat(auto-fit,minmax(300px,1fr)); gap:16px; }
  .store-card{ background:#FFFDF8; border:1px solid var(--line); padding:14px 16px; }
  .store-card h3{ font-size:13px; margin:0 0 10px; color:var(--accent); }
  .count{ font-size:12px; color:var(--ink-soft); margin-bottom:10px; }
  .kuubou-list{ background:#FFFDF8; border:1px solid var(--line); padding:14px 16px 14px 32px; font-size:13px; }
  .kuubou-list .empty{ list-style:none; margin-left:-16px; color:var(--ink-soft); }
  form.search{ display:flex; gap:8px; margin-bottom:10px; flex-wrap:wrap; }
  input[type=text],input[type=date]{ flex:1; min-width:140px; padding:12px 14px; border:1px solid var(--line); font-size:14px; background:#fff; }
  button{ padding:12px 22px; border:none; background:var(--ink); color:var(--paper); font-size:13px; letter-spacing:0.05em; cursor:pointer; }
  button:hover{ background:var(--accent); }
  .hint{ font-size:12px; color:var(--ink-soft); margin-bottom:16px; }
  .hint code{ background:var(--paper-deep); padding:1px 5px; border:1px solid var(--line); }
  .result{ background:#FFFDF8; border:1px solid var(--line); padding:20px; white-space:pre-wrap; font-size:14px; margin-bottom:10px; }
</style>
</head>
<body>
<header>
  <div class="eyebrow">MEISHIKI COMPATIBILITY NAVIGATOR</div>
  <h1>命式相性ナビ</h1>
</header>
<main>
  <section>
    <h2>検索（詳細分析・相性・チーム編成）</h2>
    <form class="search" method="get" action="/">
      <input type="text" name="q" placeholder="例：山田太郎　／　山田太郎 佐藤花子" value="${esc(q)}">
      <button type="submit">検索</button>
    </form>
    <div class="hint">
      個人の詳細分析：<code>山田太郎</code>（<code>山田太郎 今年</code>で年運も表示）／
      相性：<code>山田太郎 佐藤花子</code>／チーム編成：3名以上をスペース区切り／
      相乗効果：<code>山田太郎 相乗効果</code>
    </div>
    ${result ? `<div class="result">${esc(result)}</div>` : (q ? `<div class="result">該当するメンバーが見つかりませんでした。</div>` : '')}
  </section>

  <section>
    <h2>採用候補者チェック（中途・新卒）</h2>
    <p class="count">まだ登録していない候補者の氏名・生年月日を入力すると、既存メンバーとの相性・チームへの入り方の傾向を確認できます。</p>
    <form class="search" method="get" action="/">
      <input type="text" name="cname" placeholder="候補者氏名" value="${esc(candidateName)}">
      <input type="date" name="cbirth" value="${esc(candidateBirth)}">
      <button type="submit">候補者を分析</button>
    </form>
    ${candidateResult ? `<div class="result">${esc(candidateResult)}</div>` : ''}
  </section>

  <section>
    <h2>今月、空亡の時期にあたるメンバー（アラート・${kuubouList.length}名）</h2>
    <p class="count">良し悪しの判定ではなく「本来のリズムと違う動きをしやすい時期」という参考情報です。評価の場ではなく、雑談や1on1で近況を聞いてみることをおすすめします。</p>
    <ul class="kuubou-list">${kuubouItems || '<li class="empty">該当者なし</li>'}</ul>
  </section>

  <section>
    <h2>店舗別 メンバー一覧（全${withMeishiki.length}名）</h2>
    <div class="store-grid">${groupSections}</div>
  </section>
</main>
</body>
</html>`;
}

module.exports = { renderDashboard };
