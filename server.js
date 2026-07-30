const express = require('express');
const fs = require('fs');
const path = require('path');
const { renderDashboard } = require('./dashboard');
const { resolveQuery, replyCandidate, resolveTeamTheme } = require('./query');
const calc = require('./calculations');

const MEMBERS_PATH = path.join(__dirname, 'members.json');
const app = express();

app.get('/', (req, res) => {
  const q = (req.query.q || '').trim();
  const cname = (req.query.cname || '').trim();
  const cbirth = (req.query.cbirth || '').trim();
  const ctime = (req.query.ctime || '').trim();
  const crole = (req.query.crole || '').trim();
  const compatA = (req.query.compatA || '').trim();
  const compatB = (req.query.compatB || '').trim();
  const theme = (req.query.theme || '').trim();

  const rawMembers = JSON.parse(fs.readFileSync(MEMBERS_PATH, 'utf-8'));
  const result = q ? resolveQuery(q, rawMembers) : null;

  let candidateResult = null;
  if(cname && cbirth){
    const members = rawMembers.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth, m.time) }));
    const candidate = { name: cname, birth: cbirth, role: crole, meishiki: calc.computeMeishiki(cbirth, ctime) };
    candidateResult = replyCandidate(candidate, members);
  }

  let compatResult = null;
  if(compatA && compatB && compatA !== compatB){
    const members = rawMembers.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth, m.time) }));
    const mA = members.find(m => m.name === compatA);
    const mB = members.find(m => m.name === compatB);
    if(mA && mB){
      const r = calc.compatibilityText(mA, mB);
      compatResult = `${r.headline}\n\n${r.body}\n\n※日主同士の五行関係による簡易分析です。対話のきっかけとしてご活用ください。`;
    }
  }

  const themeResult = theme ? resolveTeamTheme(theme, rawMembers) : null;

  res.send(renderDashboard(rawMembers, {
    q, result,
    candidateName: cname, candidateBirth: cbirth, candidateTime: ctime, candidateRole: crole, candidateResult,
    compatA, compatB, compatResult,
    theme, themeResult
  }));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`server listening on ${PORT}`));
