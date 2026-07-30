const express = require('express');
const fs = require('fs');
const path = require('path');
const { renderDashboard } = require('./dashboard');
const { resolveQuery, replyCandidate } = require('./query');
const calc = require('./calculations');

const MEMBERS_PATH = path.join(__dirname, 'members.json');
const app = express();

app.get('/', (req, res) => {
  const q = (req.query.q || '').trim();
  const cname = (req.query.cname || '').trim();
  const cbirth = (req.query.cbirth || '').trim();
  const ctime = (req.query.ctime || '').trim();
  const crole = (req.query.crole || '').trim();
  const rawMembers = JSON.parse(fs.readFileSync(MEMBERS_PATH, 'utf-8'));
  const result = q ? resolveQuery(q, rawMembers) : null;

  let candidateResult = null;
  if(cname && cbirth){
    const members = rawMembers.map(m => ({ ...m, meishiki: calc.computeMeishiki(m.birth, m.time) }));
    const candidate = { name: cname, birth: cbirth, role: crole, meishiki: calc.computeMeishiki(cbirth, ctime) };
    candidateResult = replyCandidate(candidate, members);
  }

  res.send(renderDashboard(rawMembers, {
    q, result,
    candidateName: cname, candidateBirth: cbirth, candidateTime: ctime, candidateRole: crole,
    candidateResult
  }));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`server listening on ${PORT}`));
