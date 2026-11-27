import { readFile, writeFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const root = new URL('../../', import.meta.url);
const browser = JSON.parse(await readFile(new URL('reports/site-browser-tests.json', root), 'utf8'));
const contrast = {};
for (const file of await readdir(new URL('reports/site-contrast/', root))) {
  const result = JSON.parse(await readFile(new URL(`reports/site-contrast/${file}`, root), 'utf8'));
  contrast[file.replace('.json', '')] = {
    measured_pairings: result.measured.length,
    failed_pairings: result.measured.filter(pair => !pair.pass).length,
    states: [...new Set(result.measured.map(pair => pair.state))],
    scope: result.scope,
  };
}
const build = JSON.parse(await readFile(new URL('reports/site-build.json', root), 'utf8'));
const source_unchanged = (await Promise.all(Object.entries(build.source_sha256).map(async ([name, hash]) => createHash('sha256').update(await readFile(new URL(name, root))).digest('hex') === hash))).every(Boolean);
const data = {
  scope: 'Public static landing page, not fraud-platform acceptance',
  browser: browser.stats,
  contrast,
  source_unchanged_since_build_manifest: source_unchanged,
  public_files: build.files.length,
  pass: browser.stats.expected > 0 && browser.stats.unexpected === 0 && browser.stats.skipped === 0 && source_unchanged && Object.values(contrast).every(value => value.failed_pairings === 0),
};
await writeFile(new URL('reports/site-acceptance.json', root), `${JSON.stringify(data, null, 2)}\n`);
console.log(JSON.stringify(data));
if (!data.pass) process.exitCode = 1;
