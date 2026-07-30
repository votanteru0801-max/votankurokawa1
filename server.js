const express = require('express');
const fs = require('fs');
const path = require('path');
const { renderDashboard } = require('./dashboard');
const { resolveQuery } = require('./query');

const MEMBERS_PATH = path.join(__dirname, 'members.json');
const app = express();

app.get('/', (req, res) => {
  const q = (req.query.q || '').trim();
  const rawMembers = JSON.parse(fs.readFileSync(MEMBERS_PATH, 'utf-8'));
  const result = q ? resolveQuery(q, rawMembers) : null;
  res.send(renderDashboard(rawMembers, { q, result }));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`server listening on ${PORT}`));
