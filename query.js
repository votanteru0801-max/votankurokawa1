const calc = require('./calculations');

function findByName(members, text){
  return members.filter(m => text.includes(m.name) || text.includes(m.name.replace(/\s/g,'')));
}

function replyDetail(m){
  const narrative = calc.personTypeNarrative(m);
  const hint = calc.handlingHint(m);
  const q = calc.suggestedQuestions(m);
  const domain = calc.replyDomainProfile(m);
  const role = calc.roleStrengthText(m, m.role);
  let note = m.note ? `\n\n【面談メモ】\n${m.note}` : '';
  return `■${m.name}さん（${m.group || '—'}${m.role ? '／'+m.role : ''}）の詳細分析\n\n${narrative}\n\n${hint}\n\n${q}\n\n${domain}${role ? '\n'+role : ''}${note}`;
}

function replyCompat(mA, mB){
  const r = calc.compatibilityText(mA, mB);
  return `${r.headline}\n\n${r.body}\n\n※日主同士の五行関係による簡易分析です。対話のきっかけとしてご活用ください。`;
}

function replyTeam(list){
  let out = `■チーム編成メモ（${list.map(m=>m.name).join('、')}）\n\n`;
  const counts = {'木':0,'火':0,'土':0,'金':0,'水':0};
  list.forEach(m => { counts[calc.gogyoOf(m.meishiki.day.kanIdx)]++; });
  out += `【五行バランス】木${counts['木']}・火${counts['火']}・土${counts['土']}・金${counts['金']}・水${counts['水']}\n`;
  const zero = Object.entries(counts).filter(([k,v])=>v===0).map(([k])=>k);
  if(zero.length) out += `→ ${zero.join('・')}の気を持つメンバーがいないため、そのタイプの視点（${zero.map(z=>({'木':'発案・独立心','火':'発信・行動力','土':'調整・堅実さ','金':'決断力・切れ味','水':'柔軟性・自由な発想'}[z])).join('/')}）が手薄になりやすいかもしれません。\n`;
  out += `\n【ペアごとの関係性】\n`;
  for(let i=0;i<list.length;i++){
    for(let j=i+1;j<list.length;j++){
      const r = calc.compatibilityText(list[i], list[j]);
      out += `・${r.headline}\n`;
    }
  }
  out += `\n※あくまで五行理論・命式に基づく簡易分析です。実際のアサインは本人のスキル・希望を優先し、対話の参考としてご活用ください。`;
  return out;
}

function resolveQuery(text, rawMembers){
  const members = rawMembers.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth, m.time) }));
  const found = findByName(members, text);
  const wantsSynergy = text.includes('相乗効果') || text.includes('シナジー');

  if(found.length === 1 && wantsSynergy){
    return calc.replySynergySearch(found[0], members);
  }
  if(found.length === 1){
    return replyDetail(found[0]);
  }
  return null;
}

function replyCandidate(candidate, allMembers){
  const narrative = calc.personTypeNarrative(candidate);
  const hint = calc.handlingHint(candidate);
  const domain = calc.replyDomainProfile(candidate);
  const role = calc.roleStrengthText(candidate, candidate.role);
  const synergy = calc.replySynergySearch(candidate, allMembers);
  return `■候補者：${candidate.name}さんの分析\n\n${narrative}\n\n${hint}\n\n${domain}${role ? '\n'+role+'\n' : ''}\n${synergy}`;
}

const DOMAIN_KEYWORDS = {
  '技術教育': ['技術', '教育', '育成', 'メニュー開発', '新しい技術', '研修'],
  '採用': ['採用', '人材', '面接'],
  '集客': ['集客', '予約', '新規客'],
  'SNS発信': ['SNS', '発信', '投稿', 'インスタ'],
  '売上を上げる': ['売上', '営業', '利益', '数字'],
  '組織構築': ['組織', 'マネジメント', '仕組み', '運営']
};
const ROLE_ORDER = ['アシスタント','スタイリスト','店長','マネージャー'];

function findThemeDomain(text){
  for(const [domain, words] of Object.entries(DOMAIN_KEYWORDS)){
    if(words.some(w => text.includes(w))) return domain;
  }
  return null;
}
function findRoleFilter(text){
  const m = text.match(/(.+?)以上/);
  if(!m) return null;
  const roleName = m[1].trim();
  const idx = ROLE_ORDER.findIndex(r => roleName.includes(r) || r.includes(roleName));
  if(idx === -1) return null;
  return { roleName, minLevel: idx };
}

function findAnchor(text, members){
  const exact = findByName(members, text);
  if(exact.length === 1) return { anchor: exact[0], ambiguous: null };
  if(exact.length > 1) return { anchor: null, ambiguous: exact };

  // フルネームで見つからない場合、姓（スペース区切りの前半）だけでの部分一致を試す
  const bySurname = members.filter(m => {
    const surname = m.name.split(/\s+/)[0];
    return surname.length >= 2 && text.includes(surname);
  });
  if(bySurname.length === 1) return { anchor: bySurname[0], ambiguous: null };
  if(bySurname.length > 1) return { anchor: null, ambiguous: bySurname };
  return { anchor: null, ambiguous: null };
}

function resolveTeamTheme(themeText, rawMembers){
  const members = rawMembers.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth, m.time) }));
  const { anchor, ambiguous } = findAnchor(themeText, members);
  const domain = findThemeDomain(themeText);
  const roleFilter = findRoleFilter(themeText);

  if(ambiguous && ambiguous.length){
    return `■テーマ「${themeText}」\n\n名前の候補が複数見つかりました：${ambiguous.map(m=>`${m.name}（${m.group||'—'}）`).join('、')}\nお手数ですが、フルネームで指定し直してください。`;
  }

  let pool = members;
  let roleNote = '';
  if(roleFilter){
    const filtered = pool.filter(m => {
      const idx = ROLE_ORDER.findIndex(r => m.role && m.role.includes(r));
      return idx >= roleFilter.minLevel;
    });
    if(filtered.length){
      pool = filtered;
    } else {
      roleNote = `\n※「${roleFilter.roleName}以上」で絞り込もうとしましたが、役職（役職欄）が登録されているメンバーがいないため、全メンバーから選出しています。`;
    }
  }

  let scored;
  let headline;
  if(anchor){
    pool = pool.filter(m => m.name !== anchor.name);
    scored = pool.map(m => ({ m, score: calc.gogyoRelationText ? null : null }));
    scored = pool.map(m => {
      const s = calc.compatibilityText(anchor, m);
      const aIdx = calc.kanGogyoIdx(anchor.meishiki.day.kanIdx), bIdx = calc.kanGogyoIdx(m.meishiki.day.kanIdx);
      const offset = ((bIdx-aIdx)%5+5)%5;
      const score = (offset===1||offset===4) ? 3 : (offset===0 ? 1 : 2);
      return { m, score, headline: s.headline };
    }).sort((a,b)=>b.score-a.score);
    headline = `■テーマ「${themeText}」：${anchor.name}さんと相性の良いメンバー`;
  } else if(domain){
    scored = pool.map(m => ({ m, score: calc.domainProfile(m).scores[domain] || 0 })).sort((a,b)=>b.score-a.score);
    headline = `■テーマ「${themeText}」：「${domain}」に適性のあるメンバー`;
  } else {
    scored = pool.map(m => ({ m, score: 0 }));
    headline = `■テーマ「${themeText}」：該当するキーワードが見つからなかったため、ランダムに候補を表示しています`;
  }

  const top5 = scored.slice(0,5);
  let out = `${headline}\n\n`;
  top5.forEach((x,i) => {
    const p = calc.domainProfile(x.m);
    const strong = p.ranked.filter(([,s])=>s>0).map(([d])=>d).slice(0,2).join('／') || '該当なし';
    out += `${i+1}. ${x.m.name}（${x.m.group||'—'}${x.m.role ? '／'+x.m.role : ''}）｜命式上の強み：${strong}\n`;
  });
  out += roleNote;
  out += `\n※命式・五行に基づく簡易的な提案です。実際の編成は本人のスキル・希望と合わせて判断してください。`;
  return out;
}

module.exports = { resolveQuery, findByName, replyCandidate, resolveTeamTheme };
