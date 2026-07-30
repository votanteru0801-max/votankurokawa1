const calc = require('./calculations');

function esc(s){ return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

function renderDashboard(members){
  const withMeishiki = members.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth) }));

  const memberRows = withMeishiki.map(m => {
    const p = calc.domainProfile(m);
    const top = p.ranked.find(([,s]) => s > 0);
    return `<tr>
      <td>${esc(m.name)}</td>
      <td>${esc(m.group)}</td>
      <td>${calc.pillarStr(m.meishiki.year)} ${calc.pillarStr(m.meishiki.month)} ${calc.pillarStr(m.meishiki.day)}</td>
      <td><span class="tag">${calc.KAN[m.meishiki.day.kanIdx]}（${calc.gogyoOf(m.meishiki.day.kanIdx)}）</span></td>
      <td>${top ? esc(top[0]) : '—'}</td>
    </tr>`;
  }).join('');

  const domainSections = calc.ALL_DOMAINS.map(domain => {
    const scored = withMeishiki.map(m => ({ m, score: calc.domainProfile(m).scores[domain] || 0 }))
      .filter(x => x.score > 0).sort((a,b)=>b.score-a.score).slice(0,8);
    const items = scored.map((x,i) => `<li>${i+1}. ${esc(x.m.name)}（${esc(x.m.group)}）</li>`).join('');
    return `<div class="domain-card">
      <h3>${esc(domain)}</h3>
      <ol>${items || '<li class="empty">該当者なし</li>'}</ol>
    </div>`;
  }).join('');

  const today = new Date();
  const curBranch = calc.monthBranch(today.getFullYear(), today.getMonth()+1, today.getDate());
  const kuubouList = withMeishiki.filter(m => calc.kuubouBranches(m.meishiki.dayIdx60).map(i=>calc.SHI[i]).includes(curBranch));
  const kuubouItems = kuubouList.map(m => `<li>${esc(m.name)}（${esc(m.group)}）</li>`).join('');

  return `<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>命式相性ナビ｜ダッシュボード</title>
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
  .tag{ background:var(--paper-deep); padding:2px 8px; border:1px solid var(--line); font-size:11px; }
  .guide td{ vertical-align:top; }
  .guide code{ background:var(--paper-deep); padding:2px 6px; border:1px solid var(--line); color:var(--accent); }
  .domain-grid{ display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:14px; }
  .domain-card{ background:#FFFDF8; border:1px solid var(--line); padding:14px 16px; }
  .domain-card h3{ font-size:13px; margin:0 0 8px; color:var(--accent); }
  .domain-card ol{ margin:0; padding-left:18px; font-size:12.5px; }
  .domain-card .empty{ color:var(--ink-soft); list-style:none; margin-left:-18px; }
  .table-wrap{ max-height:520px; overflow-y:auto; }
  .count{ font-size:12px; color:var(--ink-soft); margin-bottom:10px; }
  .kuubou-list{ background:#FFFDF8; border:1px solid var(--line); padding:14px 16px 14px 32px; font-size:13px; }
  .kuubou-list .empty{ list-style:none; margin-left:-16px; color:var(--ink-soft); }
</style>
</head>
<body>
<header>
  <div class="eyebrow">MEISHIKI COMPATIBILITY NAVIGATOR</div>
  <h1>命式相性ナビ｜ダッシュボード</h1>
</header>
<main>
  <section>
    <h2>今月、空亡の時期にあたるメンバー（${kuubouList.length}名）</h2>
    <p class="count">良し悪しの判定ではなく「本来のリズムと違う動きをしやすい時期」という参考情報です。評価の場ではなく、雑談や1on1で近況を聞いてみることをおすすめします。</p>
    <ul class="kuubou-list">${kuubouItems || '<li class="empty">該当者なし</li>'}</ul>
  </section>

  <section>
    <h2>メンバー一覧（${withMeishiki.length}名）</h2>
    <div class="table-wrap">
      <table>
        <thead><tr><th>氏名</th><th>所属</th><th>年柱／月柱／日柱</th><th>日主</th><th>命式上の強み</th></tr></thead>
        <tbody>${memberRows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>領域別 適性ランキング</h2>
    <div class="domain-grid">${domainSections}</div>
  </section>
</main>
</body>
</html>`;
}

module.exports = { renderDashboard };
