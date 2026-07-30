const calc = require('./calculations');

function findByName(members, text){
  return members.filter(m => text.includes(m.name) || text.includes(m.name.replace(/\s/g,'')));
}

function parseYearKeyword(text){
  const now = new Date().getFullYear();
  if(text.includes('再来年')) return now + 2;
  if(text.includes('来年')) return now + 1;
  if(text.includes('今年')) return now;
  const m = text.match(/(20\d{2})年/);
  if(m) return Number(m[1]);
  return null;
}

function replyDetail(m, targetYear){
  const narrative = calc.personTypeNarrative(m);
  const hint = calc.handlingHint(m);
  const q = calc.suggestedQuestions(m);
  const deep = calc.deepManagementReport(m, targetYear);
  const domain = calc.replyDomainProfile(m);
  let note = m.note ? `\n\n【面談メモ】\n${m.note}` : '';
  return `■${m.name}さん（${m.group || '—'}）の詳細分析\n\n${narrative}\n\n${hint}\n\n${q}\n\n${domain}\n\n${deep}${note}`;
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
  out += `\n【業務適性】\n`;
  list.forEach(m => { out += `・${m.name}：${calc.domainProfile(m).ranked.filter(([,s])=>s>0).map(([d])=>d).slice(0,2).join('／') || '該当なし'}\n`; });
  out += `\n※あくまで五行理論・命式に基づく簡易分析です。実際のアサインは本人のスキル・希望を優先し、対話の参考としてご活用ください。`;
  return out;
}

function resolveQuery(text, rawMembers){
  const members = rawMembers.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth) }));
  const found = findByName(members, text);
  const targetYear = parseYearKeyword(text);
  const wantsSynergy = text.includes('相乗効果') || text.includes('シナジー');
  const matchedDomain = calc.ALL_DOMAINS.find(d => text.includes(d.replace('を上げる','')));

  if(found.length === 1 && wantsSynergy){
    return calc.replySynergySearch(found[0], members);
  }
  if(found.length === 0 && matchedDomain){
    return calc.replyDomainRanking(matchedDomain, members);
  }
  if(found.length >= 3){
    return replyTeam(found);
  }
  if(found.length === 2){
    return replyCompat(found[0], found[1]);
  }
  if(found.length === 1){
    return replyDetail(found[0], targetYear);
  }
  return null;
}

function replyCandidate(candidate, allMembers){
  const narrative = calc.personTypeNarrative(candidate);
  const hint = calc.handlingHint(candidate);
  const domain = calc.replyDomainProfile(candidate);
  const synergy = calc.replySynergySearch(candidate, allMembers);
  return `■候補者：${candidate.name}さんの分析\n\n${narrative}\n\n${hint}\n\n${domain}\n\n${synergy}`;
}

module.exports = { resolveQuery, findByName, replyCandidate };
