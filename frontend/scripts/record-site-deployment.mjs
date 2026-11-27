import { readFile, writeFile } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';

function arg(name) { return process.argv[process.argv.indexOf(name) + 1]; }
const url = new URL(arg('--url'));
const id = arg('--id');
const state = arg('--state');
const target = arg('--target');
if (url.protocol !== 'https:' || !url.hostname.endsWith('.vercel.app') || url.search || url.username || url.password || !/^dpl_[a-zA-Z0-9]+$/.test(id) || !['READY', 'ERROR'].includes(state) || !['production', 'preview'].includes(target)) throw new Error('Invalid verified deployment metadata');
const root = new URL('../../', import.meta.url);
const build = JSON.parse(await readFile(new URL('reports/site-build.json', root), 'utf8'));
const base_commit = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
const data = { provider: 'Vercel', project: 'mulenet-public', target, ready_state: state, deployment_id: id, url: url.origin, source: 'Local static build uploaded through the authenticated Vercel connector; provider status verified afterward', base_commit, includes_uncommitted_work: true, default_deployment_protection_retained: true, public_files: build.files, scope: build.scope };
await writeFile(new URL('reports/site-deployment.json', root), `${JSON.stringify(data, null, 2)}\n`);
console.log(JSON.stringify({ url: data.url, target: data.target, ready_state: state, public_files: build.files.length }));
