const express = require('express');
const fs = require('fs');
const path = require('path');
const { renderDashboard } = require('./dashboard');

const MEMBERS_PATH = path.join(__dirname, 'members.json');
const app = express();

app.get('/', (req, res) => {
  const rawMembers = JSON.parse(fs.readFileSync(MEMBERS_PATH, 'utf-8'));
  res.send(renderDashboard(rawMembers));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`server listening on ${PORT}`));
