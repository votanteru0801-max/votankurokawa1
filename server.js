require('dotenv').config();
const express = require('express');
const line = require('@line/bot-sdk');
const fs = require('fs');
const path = require('path');
const cron = require('node-cron');
const calc = require('./calculations');

const MEMBERS_PATH = path.join(__dirname, 'members.json');

const config = {
  channelAccessToken: process.env.LINE_CHANNEL_ACCESS_TOKEN,
  channelSecret: process.env.LINE_CHANNEL_SECRET
};
const client = new line.Client(config);
const app = express();

// ---------- データ読み書き ----------
function loadMembers(){
  const raw = JSON.parse(fs.readFileSync(MEMBERS_PATH, 'utf-8'));
  return raw.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth) }));
}
function saveRawMembers(rawMembers){
  fs.writeFileSync(MEMBERS_PATH, JSON.stringify(rawMembers, null, 2), 'utf-8');
}
function findByName(members, text){
  return members.filter(m => text.includes(m.name) || text.includes(m.name.replace(/\s/g,'')));
}

// ---------- 各種回答生成 ----------
function replyPersonal(m){
  const narrative = calc.personTypeNarrative(m);
  const hint = calc.handlingHint(m);
  const q = calc.suggestedQuestions(m);
  let note = m.note ? `\n\n【面談メモ】\n${m.note}` : '';
  return `■${m.name}さん（${m.group || '—'}）の命式分析\n\n${narrative}\n\n${hint}\n\n${q}${note}`;
}
function replyCompat(mA, mB){
  const r = calc.compatibilityText(mA, mB);
  return `${r.headline}\n\n${r.body}\n\n※日主同士の五行関係による簡易分析です。対話のきっかけとしてご活用ください。`;
}
function replyTeam(list){
  // ペアごとの相性 + グループ全体の五行バランス
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
  out += `\n※あくまで五行理論による簡易分析です。実際のアサインは本人のスキル・希望を優先し、対話の参考としてご活用ください。`;
  return out;
}
function replyMonthlyReport(members){
  const today = new Date();
  const curBranch = calc.monthBranch(today.getFullYear(), today.getMonth()+1, today.getDate());
  const flagged = members.filter(m => calc.kuubouBranches(m.meishiki.dayIdx60).map(i=>calc.SHI[i]).includes(curBranch));
  let out = `【${today.getFullYear()}年${today.getMonth()+1}月のご報告】\n登録メンバー${members.length}名のうち、${flagged.length}名が今月「空亡」の時期にあたっています。\n`;
  out += `これは良し悪しの判定ではなく「本来のリズムと違う動きをしやすい時期」という参考情報です。評価の場ではなく、雑談や1on1で近況を聞いてみることをおすすめします。\n`;
  if(flagged.length){
    out += `\n対象：` + flagged.map(m=>`${m.name}（${m.group||'—'}）`).join('、');
  }
  return out;
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

// ---------- コマンド解析 ----------
async function handleText(text, userId){
  const rawMembers = JSON.parse(fs.readFileSync(MEMBERS_PATH, 'utf-8'));
  const members = rawMembers.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth) }));

  // メモ追加: 「メモ 氏名 内容」
  if(text.startsWith('メモ')){
    const rest = text.replace(/^メモ\s*/, '');
    const target = rawMembers.find(m => rest.startsWith(m.name) || rest.startsWith(m.name.replace(/\s/g,'')));
    if(target){
      const content = rest.slice(target.name.length).replace(/^[\s:：]+/, '').trim() ||
                       rest.slice(target.name.replace(/\s/g,'').length).replace(/^[\s:：]+/, '').trim();
      target.note = target.note ? `${target.note}\n・${content}` : `・${content}`;
      saveRawMembers(rawMembers);
      return `${target.name}さんの面談メモに追加しました。\n「${content}」`;
    }
    return 'メモの形式は「メモ 氏名 内容」でお願いします。（例：メモ 山田太郎 最近新しい提案に積極的）';
  }

  if(text.includes('月次レポート') || text.includes('今月のレポート')){
    return replyMonthlyReport(members);
  }

  const found = findByName(members, text);
  const targetYear = parseYearKeyword(text);
  const wantsDeep = targetYear !== null || text.includes('経営装置') || text.includes('深掘り') || text.includes('マネジメント');
  const wantsSynergy = text.includes('相乗効果') || text.includes('シナジー');

  const matchedDomain = calc.ALL_DOMAINS.find(d => text.includes(d.replace('を上げる','')));

  // 「〇〇さんと相乗効果が生まれやすい人」
  if(found.length === 1 && wantsSynergy){
    return calc.replySynergySearch(found[0], members);
  }

  // 名前なし・領域名のみ（例：「集客」「技術教育」）→ 適性ランキング
  if(found.length === 0 && matchedDomain){
    return calc.replyDomainRanking(matchedDomain, members);
  }

  // 名前＋「適性」「強み」→ 個人の業務適性
  if(found.length === 1 && (text.includes('適性') || text.includes('強み') || matchedDomain)){
    return calc.replyDomainProfile(found[0]);
  }

  if(found.length >= 3){
    return replyTeam(found);
  }
  if(found.length === 2){
    return replyCompat(found[0], found[1]);
  }
  if(found.length === 1){
    return wantsDeep ? calc.deepManagementReport(found[0], targetYear) : replyPersonal(found[0]);
  }
  return 'メンバーの名前が見つかりませんでした。\n・個人分析→「山田太郎」\n・年別の経営装置化レポート→「山田太郎 今年」「山田太郎 来年」「山田太郎 2027年」\n・相性→「山田太郎 佐藤花子」\n・チーム編成→3名以上の名前を並べて送信\n・業務適性→「山田太郎 適性」または「集客」「技術教育」など領域名のみ\n・相乗効果検索→「山田太郎 相乗効果」\n・月次レポート→「月次レポート」\n・メモ追加→「メモ 山田太郎 内容」';
}

// ---------- LINE Webhook ----------
app.post('/webhook', line.middleware(config), async (req, res) => {
  try{
    const results = await Promise.all(req.body.events.map(async (event) => {
      if(event.type !== 'message' || event.message.type !== 'text') return null;
      const replyText = await handleText(event.message.text.trim(), event.source.userId);
      return client.replyMessage(event.replyToken, { type: 'text', text: replyText });
    }));
    res.json(results);
  } catch(err){
    console.error(err);
    res.status(500).end();
  }
});

app.get('/', (req,res) => res.send('meishiki linebot is running'));

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`server listening on ${PORT}`));

// ---------- 月初の自動配信（毎月1日 9:00 JST）----------
// LINE_PUSH_TARGET に配信先（グループID or ユーザーID）を設定してください
if (process.env.LINE_PUSH_TARGET) {
  cron.schedule('0 9 1 * *', async () => {
    const members = loadMembers();
    const text = replyMonthlyReport(members);
    try{
      await client.pushMessage(process.env.LINE_PUSH_TARGET, { type: 'text', text });
      console.log('monthly report pushed');
    } catch(err){ console.error('push failed', err); }
  }, { timezone: 'Asia/Tokyo' });
}
