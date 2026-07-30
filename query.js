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
  if(found.length >= 3){
    return replyTeam(found);
  }
  if(found.length === 2){
    return replyCompat(found[0], found[1]);
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

module.exports = { resolveQuery, findByName, replyCandidate };
