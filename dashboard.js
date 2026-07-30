const calc = require('./calculations');

function esc(s){ return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }

// 「■タイトル」「【見出し】本文」形式のプレーンテキストを、見やすいカードHTMLに整形
function formatResult(text){
  const lines = text.split('\n');
  let html = '';
  let label = null, body = [];
  const flush = () => {
    if(label){
      const highlight = (label === '陰陽五行' || label === '日主の性質') ? ' highlight' : '';
      html += `<div class="field${highlight}"><div class="field-label">${esc(label)}</div><div class="field-body">${esc(body.join('\n'))}</div></div>`;
    } else if(body.join('').trim()){
      html += `<p class="plain">${esc(body.join('\n'))}</p>`;
    }
    body = [];
  };
  lines.forEach(line => {
    const m = line.match(/^【(.+?)】(.*)$/);
    if(line.startsWith('■')){
      flush(); label = null;
      html += `<h3 class="result-title">${esc(line.replace(/^■/,''))}</h3>`;
    } else if(m){
      flush();
      label = m[1];
      body = [m[2]];
    } else if(line.trim() === ''){
      flush(); label = null;
    } else {
      body.push(line);
    }
  });
  flush();
  return html;
}

function renderDashboard(rawMembers, opts){
  opts = opts || {};
  const q = opts.q || '';
  const result = opts.result || null;
  const candidateName = opts.candidateName || '';
  const candidateBirth = opts.candidateBirth || '';
  const candidateTime = opts.candidateTime || '';
  const candidateRole = opts.candidateRole || '';
  const candidateResult = opts.candidateResult || null;
  const compatA = opts.compatA || '';
  const compatB = opts.compatB || '';
  const compatResult = opts.compatResult || null;
  const theme = opts.theme || '';
  const themeResult = opts.themeResult || null;

  const withMeishiki = rawMembers.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth, m.time) }));

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
  const LOW_STAGES = ['死','墓','絶'];
  const kuubouList = withMeishiki.filter(m => {
    const inKuubouMonth = calc.kuubouBranches(m.meishiki.dayIdx60).map(i=>calc.SHI[i]).includes(curBranch);
    if(!inKuubouMonth) return false;
    const dp = calc.currentDaiunPillar(m, today);
    if(!dp) return false; // 性別未設定などで大運が算出できない場合は対象外
    const stage = calc.juuniun(m.meishiki.day.kanIdx, dp.shiIdx).stage;
    return LOW_STAGES.includes(stage);
  });
  const kuubouItems = kuubouList.map(m => {
    const dp = calc.currentDaiunPillar(m, today);
    const stage = calc.juuniun(m.meishiki.day.kanIdx, dp.shiIdx).stage;
    return `<li><a href="/?q=${encodeURIComponent(m.name)}">${esc(m.name)}（${esc(m.group)}）</a> <span class="tag warn">大運：${esc(stage)}</span></li>`;
  }).join('');

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
  select{ flex:1; min-width:160px; padding:12px 14px; border:1px solid var(--line); font-size:14px; background:#fff; }
  button{ padding:12px 22px; border:none; background:var(--ink); color:var(--paper); font-size:13px; letter-spacing:0.05em; cursor:pointer; }
  button:hover{ background:var(--accent); }
  .hint{ font-size:12px; color:var(--ink-soft); margin-bottom:16px; }
  .hint code{ background:var(--paper-deep); padding:1px 5px; border:1px solid var(--line); }
  .result{ background:#FFFDF8; border:1px solid var(--line); padding:20px; font-size:14px; margin-bottom:10px; }
  .result-title{ font-family:"Hiragino Mincho ProN",serif; font-size:17px; color:var(--accent); margin:0 0 14px; padding-bottom:8px; border-bottom:1px solid var(--line); }
  .result .field{ margin-bottom:14px; }
  .result .field-label{ display:inline-block; font-size:11.5px; font-weight:bold; color:#fff; background:var(--ink); padding:2px 10px; border-radius:2px; margin-bottom:6px; letter-spacing:0.05em; }
  .result .field.highlight .field-label{ background:var(--accent); font-size:12.5px; padding:4px 12px; }
  .result .field.highlight .field-body{ font-size:15px; font-weight:bold; }
  .result .field-body{ white-space:pre-wrap; line-height:1.8; }
  .result .plain{ white-space:pre-wrap; color:var(--ink-soft); font-size:12.5px; margin:0 0 10px; }
  .tag.warn{ background:var(--accent); color:#fff; padding:2px 8px; font-size:11px; border-radius:2px; }
</style>
</head>
<body>
<header>
  <div class="eyebrow">MEISHIKI COMPATIBILITY NAVIGATOR</div>
  <h1>命式相性ナビ</h1>
</header>
<main>
  <section>
    <h2>個人の詳細分析</h2>
    <form class="search" method="get" action="/">
      <input type="text" name="q" placeholder="例：山田太郎" value="${esc(q)}">
      <button type="submit">検索</button>
    </form>
    <div class="hint">
      個人の詳細分析：<code>山田太郎</code>／相乗効果：<code>山田太郎 相乗効果</code>
    </div>
    ${result ? `<div class="result">${formatResult(result)}</div>` : (q ? `<div class="result">該当するメンバーが見つかりませんでした。</div>` : '')}
  </section>

  <section>
    <h2>相性チェック</h2>
    <form class="search" method="get" action="/">
      <select name="compatA">
        <option value="">メンバーA を選択</option>
        ${withMeishiki.map(m => `<option value="${esc(m.name)}" ${compatA===m.name?'selected':''}>${esc(m.name)}（${esc(m.group)}）</option>`).join('')}
      </select>
      <select name="compatB">
        <option value="">メンバーB を選択</option>
        ${withMeishiki.map(m => `<option value="${esc(m.name)}" ${compatB===m.name?'selected':''}>${esc(m.name)}（${esc(m.group)}）</option>`).join('')}
      </select>
      <button type="submit">相性を見る</button>
    </form>
    ${compatResult ? `<div class="result">${formatResult(compatResult)}</div>` : ''}
  </section>

  <section>
    <h2>チーム編成（テーマから5名を提案）</h2>
    <p class="count">テーマを入力すると、命式・五行の観点から5名を自動で提案します。例：「石橋と相性のいい人」「新しい技術のメニュー開発　スタイリスト以上で」</p>
    <form class="search" method="get" action="/">
      <input type="text" name="theme" placeholder="例：石橋と相性のいい人 ／ 新しい技術のメニュー開発" value="${esc(theme)}">
      <button type="submit">5名を提案</button>
    </form>
    ${themeResult ? `<div class="result">${formatResult(themeResult)}</div>` : ''}
  </section>

  <section>
    <h2>採用候補者チェック（中途・新卒）</h2>
    <p class="count">まだ登録していない候補者の氏名・生年月日を入力すると、既存メンバーとの相性・チームへの入り方の傾向を確認できます。生まれた時間・想定役職は分かれば入力してください（任意項目）。</p>
    <form class="search" method="get" action="/">
      <input type="text" name="cname" placeholder="候補者氏名" value="${esc(candidateName)}">
      <input type="date" name="cbirth" value="${esc(candidateBirth)}">
      <input type="text" name="ctime" placeholder="生まれた時間（例：14:30／任意）" value="${esc(candidateTime)}">
      <input type="text" name="crole" placeholder="想定役職（例：スタイリスト／任意）" value="${esc(candidateRole)}">
      <button type="submit">候補者を分析</button>
    </form>
    ${candidateResult ? `<div class="result">${formatResult(candidateResult)}</div>` : ''}
  </section>

  <section>
    <h2>今月、空亡かつ大運が死・墓・絶にあたるメンバー（アラート・${kuubouList.length}名）</h2>
    <p class="count">「今月が空亡」に加えて「大運（10年単位の運気）が死・墓・絶の時期」の両方が重なっているメンバーのみ表示しています。良し悪しの判定ではなく「本来のリズムが読みにくく、力を溜めている時期」という参考情報です。評価の場ではなく、雑談や1on1で近況を聞いてみることをおすすめします。（性別未登録のメンバーは大運を算出できないため対象外です）</p>
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
