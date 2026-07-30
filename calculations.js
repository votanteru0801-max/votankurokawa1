// ==============================================================
// 命式計算モジュール（干支・五行・十大主星・十二大従星・空亡・大運・時柱）
// 算命学・陰陽五行の考え方に基づく。美容室スタッフ向けに、美容師・アイリスト・
// ネイリストなど現場でイメージしやすい言葉で表現している。
// ==============================================================

const KAN = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸'];
const SHI = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥'];
const GOGYO_NAMES = ['木','火','土','金','水'];
const SHI_GOGYO_IDX = {'子':4,'丑':2,'寅':0,'卯':0,'辰':2,'巳':1,'午':1,'未':2,'申':3,'酉':3,'戌':2,'亥':4};

// 日主（生まれた日の気）の性質――美容の現場イメージで表現
const KAN_TRAITS = {
  0:'一本気で自立心が強いタイプ。技術を自分のペースでコツコツ磨き、時間をかけて指名が育っていく大器晩成型',
  1:'柔らかく気配り上手なタイプ。お客様の些細な変化にも気づきやすく、しなやかに接客できる',
  2:'明るく行動的なタイプ。サロンの雰囲気を盛り上げる存在で、施術も楽しみながらこなせる',
  3:'観察眼が鋭く感性豊かなタイプ。デザインやカラーなど繊細な仕上がりにこだわりが出やすい',
  4:'落ち着きがあり忍耐強いタイプ。長時間の施術でも安定感があり、後輩の面倒見も良い',
  5:'温厚で堅実なタイプ。お客様にも周りにも気を配れる、縁の下の力持ち',
  6:'判断がドライで的確なタイプ。曖昧を嫌い、技術やカウンセリングでもはっきり伝えられる',
  7:'現実的で粘り強いタイプ。約束や予約をきっちり守り、コツコツ結果を積み上げる',
  8:'大らかで社交的なタイプ。お客様との会話も弾みやすく、行動力と包容力を併せ持つ',
  9:'愛情深く面倒見の良いタイプ。丁寧な接客・施術で信頼を積み重ねていく'
};

function kanGogyoIdx(kanIdx){ return Math.floor(kanIdx/2); }
function kanYinYang(kanIdx){ return kanIdx % 2; }

const JUSSHIN_TABLE = {0:['比肩','劫財'],1:['食神','傷官'],2:['偏財','正財'],3:['偏官','正官'],4:['偏印','印綬']};
const SANMEI_STAR_TABLE = {0:['貫索星','石門星'],1:['鳳閣星','調舒星'],2:['禄存星','司禄星'],3:['車騎星','牽牛星'],4:['龍高星','玉堂星']};

// 十大主星の意味――美容の現場イメージで表現
const STAR_MEANING = {
  '貫索星':'自分の技術・こだわりを大事にする力。じっくり腕を磨くのが得意',
  '石門星':'チームワークを大事にする力。周りと協力しながら仕事を進めるのが得意',
  '鳳閣星':'お客様を楽しませる力。会話や雰囲気づくりでその場を明るくするのが得意',
  '調舒星':'繊細な感性を活かす力。デザインやカラーなど細やかな仕上がりへのこだわりが強い',
  '禄存星':'頼られると力を発揮するタイプ。面倒見が良く、後輩や常連客から慕われやすい',
  '司禄星':'コツコツ積み上げる力。予約管理や在庫管理など堅実な仕事にも強い',
  '車騎星':'行動で示す力。新しい技術やスタイルにも臆せず挑戦できる',
  '牽牛星':'誇りを持って仕事に取り組む力。役職や評価をしっかり意識して働ける',
  '龍高星':'新しい発想を生み出す力。トレンドを取り入れた提案が得意',
  '玉堂星':'知識・技術を深める力。丁寧に学び、後輩にも分かりやすく伝えられる'
};

function tsuuhensei(dayKanIdx, targetKanIdx){
  const offset = ((kanGogyoIdx(targetKanIdx) - kanGogyoIdx(dayKanIdx)) % 5 + 5) % 5;
  const same = kanYinYang(dayKanIdx) === kanYinYang(targetKanIdx);
  return { offset, sanmei: SANMEI_STAR_TABLE[offset][same ? 0 : 1] };
}

const CHOSEI_START = {0:11,1:6,2:2,3:9,4:2,5:9,6:5,7:0,8:8,9:3};
const STAGE_NAMES = ['長生','沐浴','冠帯','建禄','帝旺','衰','病','死','墓','絶','胎','養'];
const SANMEI_JUUNI_NAMES = ['天貴星','天洸星','天南星','天禄星','天将星','天堂星','天胡星','天極星','天庫星','天馳星','天報星','天印星'];
const STAGE_MEANING = {
  '長生':'これから伸びていく時期。新しい技術やお客様との関係が素直に育っていきやすい',
  '沐浴':'磨かれる時期。人一倍感受性が強く、悩みながら成長していく時期',
  '冠帯':'一人前になっていく時期。意欲的で、自分から前に出ていきやすい',
  '建禄':'自立していく時期。担当替えや独り立ちでも堅実に力を発揮できる',
  '帝旺':'最も勢いのある時期。指名やチームの中心として力を発揮しやすいが、頑張りすぎに注意',
  '衰':'落ち着いていく時期。経験を活かし、後輩のサポート役に回ると力を発揮しやすい',
  '病':'内省が深まる時期。施術の技術面をじっくり見つめ直すのに向いている',
  '死':'一区切りの時期。これまでのやり方を見直し、新しいスタイルを模索しやすい',
  '墓':'力を蓄える時期。焦らずじっくり技術を積み上げるのに向いている',
  '絶':'リセットされる時期。身軽で、新しい環境やポジションにも対応しやすい',
  '胎':'新しい可能性が芽生える時期。まだ形になっていない才能を秘めている',
  '養':'周りに支えられ育つ時期。人懐っこく、先輩や常連客に可愛がられやすい'
};

function juuniun(dayKanIdx, targetShiIdx){
  const start = CHOSEI_START[dayKanIdx];
  const forward = kanYinYang(dayKanIdx) === 0;
  const diff = forward ? ((targetShiIdx - start) % 12 + 12) % 12 : ((start - targetShiIdx) % 12 + 12) % 12;
  return { stage: STAGE_NAMES[diff], sanmei: SANMEI_JUUNI_NAMES[diff] };
}

const DAY_EPOCH = Date.UTC(1873,0,12);
function dayGanZhiIndex(y,m,d){
  const t = Date.UTC(y, m-1, d);
  const days = Math.floor((t - DAY_EPOCH) / 86400000);
  return ((days % 60) + 60) % 60;
}
function yearGanZhiInfo(y,m,d){
  let adjYear = y;
  if (m < 2 || (m === 2 && d < 4)) adjYear = y - 1;
  return { kanIdx: ((adjYear-4)%10+10)%10, shiIdx: ((adjYear-4)%12+12)%12, adjYear };
}
const SETSU_MD = [[2,4],[3,6],[4,5],[5,6],[6,6],[7,7],[8,8],[9,8],[10,8],[11,7],[12,7],[1,6]];
const SETSU_BRANCH = ['寅','卯','辰','巳','午','未','申','酉','戌','亥','子','丑'];
function monthBranch(y,m,d){
  const target = new Date(y,m-1,d);
  let branch = '丑';
  for (let i=0;i<SETSU_MD.length;i++){
    const [mm,dd] = SETSU_MD[i];
    const curDate = mm===1 ? new Date(y+1,0,dd) : new Date(y,mm-1,dd);
    if (target >= curDate) branch = SETSU_BRANCH[i];
  }
  return branch;
}
const YIN_ORDER = ['寅','卯','辰','巳','午','未','申','酉','戌','亥','子','丑'];
function monthGanZhiInfo(y,m,d){
  const { kanIdx: yKanIdx } = yearGanZhiInfo(y,m,d);
  const group = yKanIdx % 5;
  const startStemForYin = [2,4,6,8,0][group];
  const branch = monthBranch(y,m,d);
  const offset = YIN_ORDER.indexOf(branch);
  return { kanIdx: (startStemForYin + offset) % 10, shiIdx: SHI.indexOf(branch) };
}

// ---- 時柱（生まれた時間が分かる場合のみ）----
function parseTimeToHour(timeStr){
  if(!timeStr) return null;
  const m = String(timeStr).match(/(\d{1,2})[時:](\d{0,2})/);
  if(!m) return null;
  let h = parseInt(m[1],10);
  let mm = m[2] ? parseInt(m[2],10) : 0;
  if(isNaN(h) || h>23 || h<0) return null;
  return h + (isNaN(mm)?0:mm)/60;
}
function hourToBranchIdx(h){
  if(h>=23 || h<1) return 0;
  return Math.floor((h-1)/2)+1;
}
function hourPillarFromDayKan(dayKanIdx, timeStr){
  const h = parseTimeToHour(timeStr);
  if(h===null) return null;
  const branchIdx = hourToBranchIdx(h);
  const group = dayKanIdx % 5;
  const startStemForZi = [0,2,4,6,8][group];
  return { kanIdx: (startStemForZi + branchIdx) % 10, shiIdx: branchIdx };
}

function computeMeishiki(birthStr, timeStr){
  const [y,m,d] = birthStr.split('-').map(Number);
  const dayIdx = dayGanZhiIndex(y,m,d);
  const yearInfo = yearGanZhiInfo(y,m,d);
  const monthInfo = monthGanZhiInfo(y,m,d);
  const dayPillar = { kanIdx: dayIdx%10, shiIdx: dayIdx%12 };
  const hour = timeStr ? hourPillarFromDayKan(dayPillar.kanIdx, timeStr) : null;
  return {
    year:{kanIdx:yearInfo.kanIdx, shiIdx:yearInfo.shiIdx},
    month:{kanIdx:monthInfo.kanIdx, shiIdx:monthInfo.shiIdx},
    day: dayPillar,
    hour,
    dayIdx60: dayIdx
  };
}
function pillarStr(p){ return p ? (KAN[p.kanIdx] + SHI[p.shiIdx]) : '不明'; }
function gogyoOf(kanIdx){ return GOGYO_NAMES[kanGogyoIdx(kanIdx)]; }

const VOID_TABLE = [[10,11],[8,9],[6,7],[4,5],[2,3],[0,1]];
function kuubouBranches(dayIdx60){ return VOID_TABLE[Math.floor(dayIdx60/10)]; }

function allSetsuDatesNear(year){
  let dates=[];
  for(let yy=year-1; yy<=year+1; yy++){ SETSU_MD.forEach(([m,d])=>dates.push(new Date(yy,m-1,d))); }
  dates.sort((a,b)=>a-b);
  return dates;
}
function nearestSetsu(birthDate){
  const dates = allSetsuDatesNear(birthDate.getFullYear());
  let prev=null,next=null;
  for(const dt of dates){ if(dt<=birthDate) prev=dt; if(dt>birthDate && !next) next=dt; }
  return {prev,next};
}
function daiun(member){
  if(!member.gender || member.gender==='不明') return null;
  const [y,m,d] = member.birth.split('-').map(Number);
  const birthDate = new Date(y,m-1,d);
  const yearInfo = yearGanZhiInfo(y,m,d);
  const isMale = member.gender === '男';
  const forward = (kanYinYang(yearInfo.kanIdx)===0 && isMale) || (kanYinYang(yearInfo.kanIdx)===1 && !isMale);
  const {prev,next} = nearestSetsu(birthDate);
  const days = forward ? (next-birthDate)/86400000 : (birthDate-prev)/86400000;
  const startAge = Math.max(0, Math.round((days/3)*10)/10);
  const monthInfo = monthGanZhiInfo(y,m,d);
  let combinedIdx=0;
  for(let i=0;i<60;i++){ if(i%10===monthInfo.kanIdx && i%12===monthInfo.shiIdx){combinedIdx=i;break;} }
  const pillars=[]; let idx=combinedIdx;
  for(let i=0;i<8;i++){
    idx = forward ? (idx+1+60)%60 : (idx-1+60)%60;
    pillars.push({ startAge: Math.round((startAge+i*10)*10)/10, kanIdx: idx%10, shiIdx: idx%12 });
  }
  return {forward, pillars};
}
function currentDaiunPillar(member, today){
  const d = daiun(member);
  if(!d) return null;
  const [by,bm,bd] = member.birth.split('-').map(Number);
  let age = today.getFullYear() - by;
  if (today.getMonth()+1 < bm || (today.getMonth()+1===bm && today.getDate()<bd)) age -= 1;
  let cur = null;
  for(const p of d.pillars){ if(age >= p.startAge) cur = p; }
  return cur;
}

function gogyoRelationText(dayKanIdx, otherKanIdx){
  const dG = kanGogyoIdx(dayKanIdx), oG = kanGogyoIdx(otherKanIdx);
  const offset = ((oG-dG)%5+5)%5;
  if(offset===0) return {label:'比和', text:'同質の気が重なる巡り。得意分野がより伸びやすい反面、無理をしすぎないよう注意。'};
  if(offset===1) return {label:'食傷（発信）', text:'発想やアウトプットが活発になりやすい巡り。新しい技術・接客スタイルへの挑戦に向く。'};
  if(offset===2) return {label:'財（行動）', text:'行動力・売上への意欲が高まりやすい巡り。動く分、息切れに注意。'};
  if(offset===3) return {label:'官殺（負荷）', text:'責任やプレッシャーを感じやすい巡り。負荷はかかるが、役職・技術ともに鍛えられる。'};
  return {label:'印（補充）', text:'エネルギーが補われやすい、周りの支援を受けやすい巡り。'};
}

function compatibilityText(mA, mB){
  const aIdx = kanGogyoIdx(mA.meishiki.day.kanIdx), bIdx = kanGogyoIdx(mB.meishiki.day.kanIdx);
  const offset = ((bIdx-aIdx)%5+5)%5;
  const aName=mA.name, bName=mB.name, aG=GOGYO_NAMES[aIdx], bG=GOGYO_NAMES[bIdx];
  let headline, body;
  if(offset===0){ headline=`${aName}さんと${bName}さん：比和（同質タイプ）`; body=`日主が同じ「${aG}」。仕事の進め方や価値観が似ており、意思疎通はスムーズ。似すぎて競合しやすい面もあるため、担当や役割を分けると良い。`; }
  else if(offset===1){ headline=`${aName}さんと${bName}さん：相生（${aName}さんがサポート役）`; body=`${aName}さんの「${aG}」が${bName}さんの「${bG}」を後押し。先輩後輩やペア施術などの組み合わせで良い相乗効果。`; }
  else if(offset===4){ headline=`${aName}さんと${bName}さん：相生（${bName}さんがサポート役）`; body=`${bName}さんの「${bG}」が${aName}さんの「${aG}」を後押し。${bName}さん主導の場面で良い流れが生まれやすい。`; }
  else if(offset===2){ headline=`${aName}さんと${bName}さん：相剋（緊張感のある関係）`; body=`${aName}さんが主導権を握りやすい構図。適度な緊張は刺激にもなる。役割分担を明確に。`; }
  else { headline=`${aName}さんと${bName}さん：相剋（緊張感のある関係）`; body=`${bName}さんが主導権を握りやすい構図。率直な意見交換ができるペアになり得る。`; }
  return {headline, body};
}

// 算命学・陰陽五行のみに基づく命式分析（四柱推命名は表示しない）
function personTypeNarrative(m){
  const dayKanIdx = m.meishiki.day.kanIdx;
  const dayGogyo = gogyoOf(dayKanIdx);
  const yearStar = tsuuhensei(dayKanIdx, m.meishiki.year.kanIdx);
  const monthStar = tsuuhensei(dayKanIdx, m.meishiki.month.kanIdx);
  const monthJuuni = juuniun(dayKanIdx, m.meishiki.month.shiIdx);
  const yearJuuni = juuniun(dayKanIdx, m.meishiki.year.shiIdx);
  const kb = kuubouBranches(m.meishiki.dayIdx60).map(i=>SHI[i]);

  const lines = [];
  lines.push(`【日主】${KAN[dayKanIdx]}（${dayGogyo}の性質）：${KAN_TRAITS[dayKanIdx]}。`);
  lines.push(`【月柱】十大主星は「${monthStar.sanmei}」＝${STAR_MEANING[monthStar.sanmei]}。十二大従星は「${monthJuuni.sanmei}」で、${STAGE_MEANING[monthJuuni.stage]}。→対人関係・お店での立ち回りにこの傾向が出やすいと言えます。`);
  lines.push(`【年柱】十大主星は「${yearStar.sanmei}」＝${STAR_MEANING[yearStar.sanmei]}。十二大従星は「${yearJuuni.sanmei}」で、${STAGE_MEANING[yearJuuni.stage]}。→目上の人や生い立ちに関わる部分にこの傾向が出やすいと言えます。`);
  if(m.meishiki.hour){
    const hourStar = tsuuhensei(dayKanIdx, m.meishiki.hour.kanIdx);
    const hourJuuni = juuniun(dayKanIdx, m.meishiki.hour.shiIdx);
    lines.push(`【時柱（参考）】十大主星は「${hourStar.sanmei}」＝${STAR_MEANING[hourStar.sanmei]}。十二大従星は「${hourJuuni.sanmei}」で、${STAGE_MEANING[hourJuuni.stage]}。→晩年期や、じっくり向き合う仕事の中でこの傾向が出やすいと言えます。`);
  }
  lines.push(`【空亡】${kb.join('・')}の年月日は、本来のリズムが読みにくい時期とされます。`);
  return lines.join('\n');
}

function handlingHint(m){
  const dayKanIdx = m.meishiki.day.kanIdx;
  const monthStar = tsuuhensei(dayKanIdx, m.meishiki.month.kanIdx);
  const hintMap = {
    '貫索星':'自分のペースを尊重されると力を発揮しやすいタイプです。技術指導は「教える」より「見守って任せる」形が合いそうです。',
    '石門星':'チームの中で役割を持つとやる気が出やすいタイプです。一人で抱え込ませず、周りと組ませる施術や企画が向いています。',
    '鳳閣星':'楽しさや納得感を大事にするタイプです。理由を丁寧に伝えると、接客にも良い雰囲気が出やすくなります。',
    '調舒星':'繊細な感性を持つタイプです。お客様の前での指摘より、バックヤードで一対一でじっくり話す場が合いそうです。',
    '禄存星':'頼られることでやる気が出るタイプです。後輩の指導係や新人教育を任せると力を発揮しやすいです。',
    '司禄星':'安定志向で堅実なタイプです。急なシフト変更より、見通しを示してあげると安心して動けます。',
    '車騎星':'行動で示すタイプです。細かい説明より、まず新しい技術やお客様対応を任せてみると力を発揮しやすいです。',
    '牽牛星':'責任感が強く、役職や評価を意識するタイプです。指名数やポジションをきちんと言葉にして伝えると安心します。',
    '龍高星':'変化や新しいことに強いタイプです。同じ作業の繰り返しより、新しい技術・トレンド提案を任せると良さそうです。',
    '玉堂星':'じっくり学ぶタイプです。即戦力を求めず、練習時間や資格取得のサポートを用意すると力を発揮しやすいです。'
  };
  return `【接し方のヒント（月柱の十大主星「${monthStar.sanmei}」より）】${hintMap[monthStar.sanmei]}\n※これは断定ではなく、対話の参考として捉えてください。`;
}

function suggestedQuestions(m){
  const dayKanIdx = m.meishiki.day.kanIdx;
  const monthStar = tsuuhensei(dayKanIdx, m.meishiki.month.kanIdx);
  const qMap = {
    '貫索星':'最近、自分のやり方で施術・接客をやらせてほしいと感じる場面はある？',
    '石門星':'今のチームでの役割に納得感はある？もっと任されたいことはある？',
    '鳳閣星':'今の仕事で楽しいと感じる部分はどこ？逆に退屈に感じる部分は？',
    '調舒星':'最近、集中して取り組めている施術はある？逆に気になって仕方ないことは？',
    '禄存星':'最近、お客様や後輩の役に立てたと感じた場面はある？',
    '司禄星':'今の働き方で、もう少し見通しが欲しいと感じることはある？',
    '車騎星':'最近、もっと新しい技術に挑戦したいと感じることはある？',
    '牽牛星':'今の役職や評価について、率直にどう感じている？',
    '龍高星':'そろそろ新しいスタイルや技術に挑戦したい気持ちはある？',
    '玉堂星':'最近じっくり技術を練習したいのに時間が取れていないことはある？'
  };
  return `【1on1で聞いてみると良いかもしれない質問】\n「${qMap[monthStar.sanmei]}」\n※命式の傾向をヒントにした問いかけです。答えを決めつけず、本人の言葉で確かめてください。`;
}

// ---- 役職での強み（役職が入力されている場合のみ） ----
const ELEMENT_ROLE_HINT = {
  '木':'新しい技術やスタイルを自分から取り入れていく伸びしろ',
  '火':'お客様との会話や店内の雰囲気づくりで場を盛り上げる力',
  '土':'後輩のフォローや店内の調整役としての安定感',
  '金':'技術の正確さや、判断力を活かした的確な提案力',
  '水':'状況に応じて柔軟に対応する力や、じっくり考えて仕上げる丁寧さ'
};
function roleStrengthText(m, role){
  if(!role) return '';
  const dayKanIdx = m.meishiki.day.kanIdx;
  const element = gogyoOf(dayKanIdx);
  const monthStar = tsuuhensei(dayKanIdx, m.meishiki.month.kanIdx);
  return `【役職「${role}」としての強み】命式上は「${element}」の性質を持ち、${ELEMENT_ROLE_HINT[element]}が武器になりそうです。あわせて「${monthStar.sanmei}」の傾向（${STAR_MEANING[monthStar.sanmei]}）も、${role}という役割の中で活きやすいポイントです。\n※役職への適性は経験やご本人の希望も大きく影響します。あくまで命式からみた参考傾向としてご活用ください。`;
}

// ==============================================================
// 業務適性マップ（陰陽五行・十大主星ベース）
// ==============================================================
const DOMAIN_MAP = {
  0: { same: '採用（人を惹きつけ、見極める力）', diff: '採用（競い合いながら人を巻き込む力）' },
  1: { same: '集客（お客様を楽しませ、惹きつける力）', diff: 'SNS発信（鋭い感性で言葉や表現に落とし込む力）' },
  2: { same: '売上を上げる（機動力のある行動で稼ぐ力）', diff: '売上を上げる（堅実に積み上げて稼ぐ力）' },
  3: { same: '組織構築（突破力で仕組みを変える力）', diff: '組織構築（規律と信頼で仕組みを守る力）' },
  4: { same: '技術教育（独自の視点で教える力）', diff: '技術教育（体系立てて伝える力）' }
};
const ALL_DOMAINS = ['採用','集客','SNS発信','売上を上げる','組織構築','技術教育'];

function domainScoreDetail(dayKanIdx, targetKanIdx, pillarLabel){
  const offset = ((kanGogyoIdx(targetKanIdx) - kanGogyoIdx(dayKanIdx)) % 5 + 5) % 5;
  const same = kanYinYang(dayKanIdx) === kanYinYang(targetKanIdx);
  const full = DOMAIN_MAP[offset][same ? 'same' : 'diff'];
  return { domain: full.split('（')[0], reason: `${pillarLabel}が${full}` };
}
function approxBranchKanIdx(shiIdx, dayKanIdx){
  const gogyoIdx = SHI_GOGYO_IDX[SHI[shiIdx]];
  return gogyoIdx*2 + kanYinYang(dayKanIdx);
}
function domainProfile(m){
  const dayKanIdx = m.meishiki.day.kanIdx;
  const signals = [
    domainScoreDetail(dayKanIdx, m.meishiki.year.kanIdx, '年柱'),
    domainScoreDetail(dayKanIdx, m.meishiki.month.kanIdx, '月柱'),
    domainScoreDetail(dayKanIdx, approxBranchKanIdx(m.meishiki.day.shiIdx, dayKanIdx), '日支（簡易推定）')
  ];
  const scores = {};
  ALL_DOMAINS.forEach(d => scores[d] = 0);
  signals.forEach(s => { scores[s.domain] = (scores[s.domain]||0) + 1; });
  const ranked = Object.entries(scores).sort((a,b)=>b[1]-a[1]);
  return { scores, ranked, signals };
}
function replyDomainProfile(m){
  const p = domainProfile(m);
  let out = `【命式上の強み】\n`;
  p.ranked.slice(0,2).forEach(([d,score]) => { if(score>0) out += `・${d}（該当${score}件）\n`; });
  out += `\n【根拠】\n`;
  p.signals.forEach(s => out += `・${s.reason}\n`);
  return out;
}
function synergyScore(mA, mB){
  const aIdx = kanGogyoIdx(mA.meishiki.day.kanIdx), bIdx = kanGogyoIdx(mB.meishiki.day.kanIdx);
  const offset = ((bIdx-aIdx)%5+5)%5;
  const gogyoScore = (offset===1||offset===4) ? 3 : (offset===0 ? 1 : 2);
  const domainA = domainProfile(mA).ranked[0][0];
  const domainB = domainProfile(mB).ranked[0][0];
  const domainBonus = domainA !== domainB ? 1 : 0;
  return { total: gogyoScore + domainBonus, gogyoScore, domainA, domainB, offset };
}
function replySynergySearch(m, allMembers){
  const others = allMembers.filter(x => x.name !== m.name);
  const scored = others.map(o => ({ o, s: synergyScore(m, o) })).sort((a,b)=>b.s.total-a.s.total);
  const top = scored.slice(0,5);
  const myDomain = domainProfile(m).ranked[0][0];
  let out = `■${m.name}さん（強み：${myDomain}）と相乗効果が生まれやすいメンバー\n\n`;
  top.forEach((x,i) => {
    const rel = gogyoRelationText(m.meishiki.day.kanIdx, x.o.meishiki.day.kanIdx);
    out += `${i+1}. ${x.o.name}（${x.o.group||'—'}）｜五行関係：${rel.label}｜強み：${x.s.domainB}${x.s.domainA!==x.s.domainB ? '（異なる強みで補完し合える組み合わせ）' : ''}\n`;
  });
  out += `\n※五行の相性と、命式上の強みの違い（補完関係）から算出した簡易分析です。実際の組み合わせは対話と実績を踏まえて判断してください。`;
  return out;
}

module.exports = {
  KAN, SHI, GOGYO_NAMES,
  kanGogyoIdx, kanYinYang, tsuuhensei, juuniun,
  computeMeishiki, pillarStr, gogyoOf, kuubouBranches,
  daiun, currentDaiunPillar, gogyoRelationText,
  compatibilityText, personTypeNarrative, handlingHint, suggestedQuestions,
  roleStrengthText, monthBranch,
  domainProfile, replyDomainProfile, replySynergySearch, ALL_DOMAINS
};
