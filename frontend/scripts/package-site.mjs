import { readFile, readdir, lstat, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';

const root = new URL('../dist-site/', import.meta.url);
const top = new Set(['index.html', 'vercel.json', 'evidence.json', 'evidence-graph-alpha.png', 'favicon.svg', 'IBM-Plex-LICENSE.txt', 'IBM-Plex-Mono-LICENSE.txt']);
const files = [];
async function walk(relative = '') {
  for (const entry of await readdir(new URL(relative, root), { withFileTypes: true })) {
    const name = `${relative}${entry.name}`;
    const url = new URL(name, root);
    if ((await lstat(url)).isSymbolicLink()) throw new Error(`Refusing symlink: ${name}`);
    if (entry.isDirectory()) {
      if (name !== 'assets') throw new Error(`Unexpected public directory: ${name}`);
      await walk('assets/');
    } else {
      if (!top.has(name) && !/^assets\/[a-zA-Z0-9_-]+\.(js|css|woff2?)$/.test(name)) throw new Error(`Not allowlisted: ${name}`);
      const data = await readFile(url);
      files.push({ file: name, size: data.length, sha: createHash('sha1').update(data).digest('hex'), sha256: createHash('sha256').update(data).digest('hex') });
    }
  }
}
await walk();
files.sort((a, b) => a.file.localeCompare(b.file));
const source_sha256 = {};
for (const source of ['website/main.jsx', 'website/site.css', 'website/index.html', 'vite.site.config.js', 'package.json', 'package-lock.json', 'scripts/render-site-evidence.mjs']) {
  const data = await readFile(new URL(`../${source}`, import.meta.url));
  source_sha256[`frontend/${source}`] = createHash('sha256').update(data).digest('hex');
}
const manifest = { scope: 'Public static landing page only. No backend, application entry, model, dataset, environment file or credentials.', source_sha256, files };
if (process.argv.includes('--part')) {
  const index = Number(process.argv[process.argv.indexOf('--part') + 1]);
  const offset = Number(process.argv[process.argv.indexOf('--offset') + 1]);
  if (!Number.isInteger(index) || index < 0 || index >= files.length || !Number.isInteger(offset) || offset < 0) throw new Error('Invalid part request');
  const encoded = (await readFile(new URL(files[index].file, root))).toString('base64');
  process.stdout.write(encoded.slice(offset, offset + 24000));
} else {
  await writeFile(new URL('../../reports/site-build.json', import.meta.url), `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(JSON.stringify(manifest));
}
