import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';

const root = new URL('../../', import.meta.url);
const sources = {};
async function report(name) {
  const bytes = await readFile(new URL(`reports/${name}.json`, root));
  sources[`reports/${name}.json`] = createHash('sha256').update(bytes).digest('hex');
  return JSON.parse(bytes);
}
const paysim = await report('metrics-paysim-temporal');
const temporal = await report('metrics-sim-temporal');
const entity = await report('metrics-sim-entity');
function metrics(model) {
  const selected = {};
  for (const name of ['pr_auc', 'recall', 'fpr']) {
    const value = model.metrics[name];
    if (!Number.isFinite(value.value) || !value.ci95.every(Number.isFinite)) {
      throw new Error(`Missing measured ${name}; refusing to publish substitute figures`);
    }
    selected[name] = value;
  }
  return selected;
}
function simulator(input, split) {
  const candidate = input.models.tabular_graph;
  return { dataset: 'Local account simulator', split, model: 'XGBoost + graph features', ...metrics(candidate) };
}
const evidence = {
  data_provenance: 'synthetic',
  source_sha256: sources,
  paysim: {
    dataset: 'PaySim', split: 'temporal', model: 'XGBoost, pre-transfer inputs',
    task: paysim.metadata.task, test_rows: paysim.metadata.counts.test,
    threshold: paysim.models.pre_transfer.threshold,
    ...metrics(paysim.models.pre_transfer),
    limitations: paysim.metadata.limitations,
  },
  simulator: [simulator(temporal, 'temporal'), simulator(entity, 'entity-disjoint')],
  notes: [
    'Simulated transaction classification is not validation of future account or ring detection.',
    'Thresholds were selected on validation data, not the test set.',
    'Intervals are row-bootstrap 95% confidence intervals; account and temporal dependence are not modeled.',
    'The local account simulator recorded no test recall at its selected strict operating point.',
    'The GNN did not earn the selected default path. Full-network AMLworld performance remains unmeasured.',
    'No real financial recovery, customer deployment or direct I4C/NCRP access is claimed.',
  ],
};
const output = `${JSON.stringify(evidence, null, 2)}\n`;
for (const relative of ['reports/site-evidence.json', 'frontend/website/public/evidence.json']) {
  const url = new URL(relative, root);
  if (process.argv.includes('--check')) {
    if (await readFile(url, 'utf8') !== output) throw new Error(`Stale generated evidence: ${relative}`);
  } else {
    await mkdir(new URL('./', url), { recursive: true });
    await writeFile(url, output);
  }
}
console.log(`PASS: ${process.argv.includes('--check') ? 'checked' : 'generated'} public evidence from ${Object.keys(sources).length} measured reports (${fileURLToPath(root)})`);
