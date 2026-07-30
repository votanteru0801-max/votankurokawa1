// ==============================================================
// 命式計算モジュール（干支・五行・通変星/十大主星・十二運/十二大従星・空亡・大運）
// 標準的な四柱推命の暦計算に基づく。算命学の十大主星・十二大従星は
// 名称のみ異なる同一の算出方法（日干を基準にした通変星／十二運）を採用。
// ==============================================================

const KAN = ['甲','乙','丙','丁','戊','己','庚','辛','壬','癸'];
const SHI = ['子','丑','寅','卯','辰','巳','午','未','申','酉','戌','亥'];
const GOGYO_NAMES = ['木','火','土','金','水'];
const SHI_GOGYO_IDX = {'子':4,'丑':2,'寅':0,'卯':0,'辰':2,'巳':1,'午':1,'未':2,'申':3,'酉':3,'戌':2,'亥':4};

const KAN_TRAITS = {
  0:'健全な野心と自立心。マイペースだが着実に積み上げる大器晩成型',
  1:'穏やかで柔軟。人の気持ちを察する力があり、しなやかに物事を進める',
  2:'明るく行動的。集団の中でも目立ち、物事を楽しむエネルギーがある',
  3:'知的で観察力に優れるが、内面は情熱的で繊細な一面もある',
  4:'落ち着きがあり忍耐強い。信頼されやすく、人の世話を焼くのが好き',
  5:'温厚で堅実。人間関係では自ら折れることも厭わない気配り屋',
  6:'知性的でドライな判断力。曖昧なことを嫌い、意志が強い',
  7:'現実的で粘り強い。感情に流されず、義理堅く約束を守る',
  8:'大らかで社交的。自由を求め、行動力と包容力を併せ持つ',
  9:'穏やかで愛情深く、人の面倒をよく見る。正直で規則を重んじる'
};

function kanGogyoIdx(kanIdx){ return Math.floor(kanIdx/2); }
function kanYinYang(kanIdx){ return kanIdx % 2; } // 0=陽 1=陰

// 通変星（四柱推命）／十大主星（算命学）: 算出方法は同一、名称のみ異なる
const JUSSHIN_TABLE = {0:['比肩','劫財'],1:['食神','傷官'],2:['偏財','正財'],3:['偏官','正官'],4:['偏印','印綬']};
const SANMEI_STAR_TABLE = {0:['貫索星','石門星'],1:['鳳閣星','調舒星'],2:['禄存星','司禄星'],3:['車騎星','牽牛星'],4:['龍高星','玉堂星']};
const STAR_MEANING = {
  '比肩':'自立・対等な関係','劫財':'競争心・分かち合い',
  '貫索星':'自我・忍耐・不器用な誠実さ','石門星':'協調性・チームワーク・社交性',
  '食神':'表現力・楽しむ力','傷官':'鋭い感性・批評眼',
  '鳳閣星':'自由・大らかさ・遊び心','調舒星':'繊細な感性・芸術性・集中力',
  '偏財':'行動力・機動力のある財運','正財':'堅実な財運・安定志向',
  '禄存星':'面倒見の良さ・カリスマ性','司禄星':'堅実・家庭的・倹約',
  '偏官':'負荷を力に変える突破力','正官':'責任感・規律・信頼',
  '車騎星':'行動力・竹を割ったような気性','牽牛星':'誇り・品位・組織への忠実さ',
  '偏印':'独自の発想・専門性','印綬':'学び・受容・支援を得る力',
  '龍高星':'自由な発想・変化を恐れない改革志向','玉堂星':'知的好奇心・学問・伝統への敬意'
};

function tsuuhensei(dayKanIdx, targetKanIdx){
  const offset = ((kanGogyoIdx(targetKanIdx) - kanGogyoIdx(dayKanIdx)) % 5 + 5) % 5;
  const same = kanYinYang(dayKanIdx) === kanYinYang(targetKanIdx);
  return {
    offset,
    jusshin: JUSSHIN_TABLE[offset][same ? 0 : 1],
    sanmei: SANMEI_STAR_TABLE[offset][same ? 0 : 1]
  };
}

// ---- 十二運（四柱推命）／十二大従星（算命学） ----
const CHOSEI_START = {0:11,1:6,2:2,3:9,4:2,5:9,6:5,7:0,8:8,9:3}; // 各日干の「長生」開始地支index
const STAGE_NAMES = ['長生','沐浴','冠帯','建禄','帝旺','衰','病','死','墓','絶','胎','養'];
const SANMEI_JUUNI_NAMES = ['天貴星','天洸星','天南星','天禄星','天将星','天堂星','天胡星','天極星','天庫星','天馳星','天報星','天印星'];
const STAGE_MEANING = {
  '長生':'誕生・成長のエネルギー。素直に伸びていく力がある時期／立場',
  '沐浴':'洗われ磨かれる時期。感受性が強く、迷いも生まれやすい',
  '冠帯':'成人し力をつける時期。意欲的で自己主張が強まる',
  '建禄':'一人前として自立する時期。堅実に実力を発揮できる',
  '帝旺':'最も勢いが強い時期。統率力を発揮しやすいが強すぎる面も',
  '衰':'勢いが落ち着く時期。経験を活かし、穏やかに構える',
  '病':'内省が深まる時期。繊細で、内面に意識が向きやすい',
  '死':'一区切りの時期。物事を深く見つめ、達観しやすい',
  '墓':'蓄える時期。慎重で、じっくり物事に取り組む',
  '絶':'一度リセットされる時期。身軽で変化に対応しやすい',
  '胎':'新しい可能性を宿す時期。柔軟で多面的な才能を持つ',
  '養':'守られ育つ時期。人懐っこく、周囲の支援を受けやすい'
};

function juuniun(dayKanIdx, targetShiIdx){
  const start = CHOSEI_START[dayKanIdx];
  const forward = kanYinYang(dayKanIdx) === 0; // 陽干=順行 陰干=逆行
  const diff = forward ? ((targetShiIdx - start) % 12 + 12) % 12 : ((start - targetShiIdx) % 12 + 12) % 12;
  return { stage: STAGE_NAMES[diff], sanmei: SANMEI_JUUNI_NAMES[diff] };
}

// ---- 干支暦の基礎計算 ----
const DAY_EPOCH = Date.UTC(1873,0,12); // 甲子日
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
function computeMeishiki(birthStr){
  const [y,m,d] = birthStr.split('-').map(Number);
  const dayIdx = dayGanZhiIndex(y,m,d);
  const yearInfo = yearGanZhiInfo(y,m,d);
  const monthInfo = monthGanZhiInfo(y,m,d);
  return {
    year:{kanIdx:yearInfo.kanIdx, shiIdx:yearInfo.shiIdx},
    month:{kanIdx:monthInfo.kanIdx, shiIdx:monthInfo.shiIdx},
    day:{kanIdx:dayIdx%10, shiIdx:dayIdx%12},
    dayIdx60: dayIdx
  };
}
function pillarStr(p){ return KAN[p.kanIdx] + SHI[p.shiIdx]; }
function gogyoOf(kanIdx){ return GOGYO_NAMES[kanGogyoIdx(kanIdx)]; }

// ---- 空亡（旬空／算命学でいう天中殺の日柱ベース版） ----
const VOID_TABLE = [[10,11],[8,9],[6,7],[4,5],[2,3],[0,1]];
function kuubouBranches(dayIdx60){ return VOID_TABLE[Math.floor(dayIdx60/10)]; }

// ---- 大運（簡易計算・節入り時刻は概算） ----
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

// ---- 五行の相生相剋による関係性テキスト ----
function gogyoRelationText(dayKanIdx, otherKanIdx){
  const dG = kanGogyoIdx(dayKanIdx), oG = kanGogyoIdx(otherKanIdx);
  const offset = ((oG-dG)%5+5)%5;
  if(offset===0) return {label:'比和', text:'同質の気が重なる関係。得意分野が伸びやすい反面、似すぎて競合することも。'};
  if(offset===1) return {label:'食傷（発信）', text:'発想やアウトプットが活発になりやすい関係。新しい挑戦や発信に向く。'};
  if(offset===2) return {label:'財（行動）', text:'行動力・成果への意欲が高まりやすい関係。動く分、息切れに注意。'};
  if(offset===3) return {label:'官殺（負荷）', text:'責任やプレッシャーを感じやすい関係。負荷はかかるが鍛えられる。'};
  return {label:'印（補充）', text:'エネルギーが補われやすい、支援を受けやすい関係。'};
}

// ---- 相性診断 ----
function compatibilityText(mA, mB){
  const aIdx = kanGogyoIdx(mA.meishiki.day.kanIdx), bIdx = kanGogyoIdx(mB.meishiki.day.kanIdx);
  const offset = ((bIdx-aIdx)%5+5)%5;
  const aName=mA.name, bName=mB.name, aG=GOGYO_NAMES[aIdx], bG=GOGYO_NAMES[bIdx];
  let headline, body;
  if(offset===0){ headline=`${aName}さんと${bName}さん：比和（同質タイプ）`; body=`日主が同じ「${aG}」。価値観や仕事の進め方が似ており意思疎通はスムーズ。似すぎて競合しやすい面もあるため役割を分けると良い。`; }
  else if(offset===1){ headline=`${aName}さんと${bName}さん：相生（${aName}さんがサポート役）`; body=`${aName}さんの「${aG}」が${bName}さんの「${bG}」を後押し。上司部下やメンター的な組み合わせで良い相乗効果。`; }
  else if(offset===4){ headline=`${aName}さんと${bName}さん：相生（${bName}さんがサポート役）`; body=`${bName}さんの「${bG}」が${aName}さんの「${aG}」を後押し。${bName}さん主導の場面で良い流れが生まれやすい。`; }
  else if(offset===2){ headline=`${aName}さんと${bName}さん：相剋（緊張感のある関係）`; body=`${aName}さんが主導権を握りやすい構図。適度な緊張は刺激にもなる。役割分担を明確に。`; }
  else { headline=`${aName}さんと${bName}さん：相剋（緊張感のある関係）`; body=`${bName}さんが主導権を握りやすい構図。率直な議論ができるペアになり得る。`; }
  return {headline, body};
}

// ---- 個人の深掘り分析（十大主星・十二運の根拠付き） ----
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
  lines.push(`【月柱】十干は「${monthStar.sanmei}」（四柱推命名：${monthStar.jusshin}）＝${STAR_MEANING[monthStar.sanmei]}の傾向。十二運は「${monthJuuni.stage}」（算命学名：${monthJuuni.sanmei}）で、${STAGE_MEANING[monthJuuni.stage]}。→対人関係・社会での立ち回りにこの傾向が出やすいと言えます。`);
  lines.push(`【年柱】十干は「${yearStar.sanmei}」（四柱推命名：${yearStar.jusshin}）＝${STAR_MEANING[yearStar.sanmei]}の傾向。十二運は「${yearJuuni.stage}」（算命学名：${yearJuuni.sanmei}）で、${STAGE_MEANING[yearJuuni.stage]}。→目上の人や生い立ちに関わる部分にこの傾向が出やすいと言えます。`);
  lines.push(`【空亡】${kb.join('・')}の年月日は、本来のリズムが読みにくい時期とされます。`);
  return lines.join('\n');
}

// 「取り扱い方」＝接し方のヒント（断定ではなく提案として）
function handlingHint(m){
  const dayKanIdx = m.meishiki.day.kanIdx;
  const monthStar = tsuuhensei(dayKanIdx, m.meishiki.month.kanIdx);
  const hintMap = {
    '貫索星':'自分のペースを尊重されると力を発揮しやすいタイプです。命令より「任せる」形が合いそうです。',
    '石門星':'チームの中で役割を持つとやる気が出やすいタイプです。一人で抱え込ませないことがポイントです。',
    '鳳閣星':'楽しさや納得感を大事にするタイプです。理由を丁寧に伝えると動きやすくなりそうです。',
    '調舒星':'繊細な感性を持つタイプです。頭ごなしの指摘より、一対一でじっくり話す場が合いそうです。',
    '禄存星':'頼られることでやる気が出るタイプです。感謝を言葉で伝えると関係が安定しやすいです。',
    '司禄星':'安定志向で堅実なタイプです。急な変更より、見通しを示してあげると安心して動けます。',
    '車騎星':'行動で示すタイプです。細かい説明より、まず任せてみると力を発揮しやすいです。',
    '牽牛星':'責任感が強く、評価や役職を意識するタイプです。きちんと役割を明示すると安心します。',
    '龍高星':'変化や新しいことに強いタイプです。同じことの繰り返しより新しい挑戦を用意すると良さそうです。',
    '玉堂星':'じっくり考えるタイプです。即断即決を求めず、考える時間を用意すると力を発揮しやすいです。'
  };
  return `【接し方のヒント（月柱の十大主星「${monthStar.sanmei}」より）】${hintMap[monthStar.sanmei]}\n※これは断定ではなく、対話の参考として捉えてください。`;
}

// 1on1で聞くと良いかもしれない質問（「まだ言い出していないこと」を"予言"せず、問いかけで引き出す代替案）
function suggestedQuestions(m){
  const dayKanIdx = m.meishiki.day.kanIdx;
  const monthStar = tsuuhensei(dayKanIdx, m.meishiki.month.kanIdx);
  const qMap = {
    '貫索星':'最近、自分のやり方でやらせてほしいと感じる場面はある？',
    '石門星':'今のチームでの役割に納得感はある？もっと任されたいことはある？',
    '鳳閣星':'今の仕事で楽しいと感じる部分はどこ？逆に退屈に感じる部分は？',
    '調舒星':'最近、集中して取り組めていることはある？逆に気になって仕方ないことは？',
    '禄存星':'最近、誰かの役に立てたと感じた場面はある？',
    '司禄星':'今の働き方で、もう少し見通しが欲しいと感じることはある？',
    '車騎星':'最近、もっと動きたい・挑戦したいと感じることはある？',
    '牽牛星':'今の役職や評価について、率直にどう感じている？',
    '龍高星':'そろそろ新しいことに挑戦したい気持ちはある？',
    '玉堂星':'最近じっくり考えたいのに時間が取れていないことはある？'
  };
  return `【1on1で聞いてみると良いかもしれない質問】\n「${qMap[monthStar.sanmei]}」\n※命式の傾向をヒントにした問いかけです。答えを決めつけず、本人の言葉で確かめてください。`;
}

module.exports = {
  KAN, SHI, GOGYO_NAMES,
  kanGogyoIdx, kanYinYang, tsuuhensei, juuniun,
  computeMeishiki, pillarStr, gogyoOf, kuubouBranches,
  daiun, currentDaiunPillar, gogyoRelationText,
  compatibilityText, personTypeNarrative, handlingHint, suggestedQuestions,
  monthBranch
};
