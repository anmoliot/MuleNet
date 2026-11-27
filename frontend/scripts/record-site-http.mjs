import { readFile, writeFile } from 'node:fs/promises';

const checks = JSON.parse(process.argv[2]);
const deployment = process.argv[3];
if (!/^dpl_[a-zA-Z0-9]+$/.test(deployment)) throw new Error('Missing verified deployment ID');
const build = JSON.parse(await readFile(new URL('../../reports/site-build.json', import.meta.url), 'utf8'));
const javascript = build.files.find(file => /^assets\/index-.*\.js$/.test(file.file));
const stylesheet = build.files.find(file => /^assets\/index-.*\.css$/.test(file.file));
if (!javascript || !stylesheet) throw new Error('Missing public build entries');
const expected = new Map([
  ['/evidence.json', 200],
  [`/${javascript.file}`, 200],
  [`/${stylesheet.file}`, 200],
  ['/evidence-graph-alpha.png', 200],
  ['/api/v1/score', 404],
  ['/api/demo/seed', 404],
]);
const pass = checks.length === expected.size && new Set(checks.map(check => check.path)).size === expected.size && checks.every(check => expected.get(check.path) === check.status && check.nosniff === 'nosniff' && check.csp.includes("default-src 'none'")) && checks.find(check => check.path === '/evidence.json')?.provenance === 'synthetic';
const result = { source: 'Authenticated Vercel connector HTTP GET results, not an unauthenticated availability claim or deployed-browser certification', deployment_id: deployment, checks, pass };
await writeFile(new URL('../../reports/site-http.json', import.meta.url), `${JSON.stringify(result, null, 2)}\n`);
console.log(JSON.stringify({ pass, checks: checks.length }));
if (!pass) process.exitCode = 1;
