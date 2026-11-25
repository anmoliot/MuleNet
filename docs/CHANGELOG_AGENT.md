# Agent Execution Log

## Phase 0: Evidence Audit

Baseline: `85b10e6e5df87f6ce7f44bb2ea6e12e66d65cf8a`.
Changes: docs/AUDIT.md, docs/ARCHITECTURE.md, docs/DECISIONS.md, this log.
No application code, dependency, model, infrastructure, or README changes.

Commands and observed summaries:

```text
Get-Item -LiteralPath C:\Users\Anmol\OneDrive\Desktop\MuleNet
FAIL: configured path did not exist.
git ls-remote https://github.com/anmoliot/MuleNet.git HEAD
Sandbox DNS failed; approved retry succeeded at the baseline SHA above.
git clone https://github.com/anmoliot/MuleNet.git C:\Users\Anmol\OneDrive\Desktop\MuleNet
PASS: fresh clone, no existing local files overwritten.
git status --short --branch
PASS: clean main tracking origin/main before docs edits.
git switch -c phase-0-audit
Sandbox .git write denied; approved retry succeeded.
rg --files -g AGENTS.md -g '!node_modules/**' -g '!venv/**' -g '!**/__pycache__/**'
No repository AGENTS.md found.
rg -n 'GATv2|GATConv|GINEConv|NeighborLoader|torch_geometric|import torch|tanh|model_metadata|train_test_split|time_split|best_threshold' ml_service MuleNet_Kaggle_Trainer.ipynb
No PyG implementation/export found; offline tanh/ridge and random split found.
git ls-files .github reports '*csv' '*env*' '*lock*' '*train_gnn*' '*train_xgboost*' '*Keycloak*'
Only plotted legacy metrics under reports; no CSV data or train_gnn/train_xgboost modules.
Get-Command python,uv,docker,java,mvn,node,npm,make,gitleaks -ErrorAction SilentlyContinue
Python, Java (default Java 8), Maven, Node, npm found.
uv, Docker CLI, make and gitleaks not found in PATH. Not acceptance evidence for runtime stack.
```

Source inspection used Get-Content and rg -n on training, serving, config, schema,
controllers, policies, Kafka/Celery, frontend, CI, and tracked metadata. Detailed
file:line quotations are in AUDIT.md. No historical metric was reproduced or
endorsed. No live auth/seed/freeze operation was invoked.

Acceptance check (PowerShell, exit 0):

```powershell
$ErrorActionPreference='Stop'; $audit = Get-Content docs/AUDIT.md -Raw; $refs = [regex]::Matches($audit, '\| `([^`]+):(\d+)` \| `(.+?)` \|'); foreach ($ref in $refs) { $source = Get-Content -LiteralPath $ref.Groups[1].Value; $line = [int]$ref.Groups[2].Value; if ($line -gt $source.Count -or -not $source[$line-1].Contains($ref.Groups[3].Value)) { throw "Invalid evidence: $($ref.Value)" } }; if ($refs.Count -ne 60) { throw 'Incomplete audit' }; Write-Output "PASS: $($refs.Count) exact file:line quotations"; $changed = @(git status --porcelain); if ($changed | Where-Object { $_ -notmatch '^\?\? docs/' }) { throw 'Non-doc change in Phase 0' }; Write-Output 'PASS: docs-only Phase 0'; git diff --check
```

Output: `PASS: 60 exact file:line quotations`; `PASS: docs-only Phase 0`;
diff whitespace check clean. Line references were mechanically reconciled against
exact source substrings, then independently verified. Initial verification found
incorrect offsets; these were corrected before acceptance. This is documentation
acceptance only, not passing application/integration/security/evaluation tests.

Claims removed/downgraded: audit quarantines historical performance, recovery,
direct-registry, real-data and GNN-attribution claims; README rewrite is Phase 8.

## Phase 1: Reference Data Foundation

Branch: phase-1-data-foundation, based on the Phase 0 audit commit.
Scope: shared deterministic as-of features, future-window labels, leakage checks,
strict CSV/JSON loaders, opt-in typology simulation, batch materialization and an
isolated authenticated feature-only HTTP factory. This is not a replacement for
the legacy scoring service and not a model-performance benchmark.

Files changed:

- .gitignore (local dataset/cache exclusions).
- ml_service/mulenet_core/__init__.py, schema.py, graph.py, features.py, labels.py, splits.py, io.py.
- ml_service/simulation/__init__.py, generator.py.
- ml_service/training/build_dataset.py and ml_service/feature_service.py.
- ml_service/tests/test_features_parity.py, test_splits_no_leakage.py, test_dataset_io.py, test_data_download.py.
- scripts/download_data.py and scripts/verify_data_foundation.py.
- data/README.md, docs/FEATURE_CONTRACT.md, docs/DECISIONS.md, docs/DOD_CHECKLIST.md and this log.
- reports/phase1-foundation.json (generated, never hand-edited).

Commands and output summaries:

```text
git switch -c phase-1-data-foundation
PASS: separate phase branch; main untouched.
python -m pytest ml_service/tests/test_features_parity.py ml_service/tests/test_splits_no_leakage.py ml_service/tests/test_dataset_io.py -q
PASS: initial feature/split/loader suite, before HTTP/downloader and additional oracle coverage.
python scripts/verify_data_foundation.py
PASS: 15 tests, including 1,000 randomized offline/online as-of comparisons at absolute tolerance 1e-9, zero relative tolerance; no skipped tests.
PASS: future-edge/label independence, hand-computed feature oracles, temporal purging, component/ring isolation, malicious leakage injection rejection.
PASS: strict feature HTTP contract, missing/arbitrary credentials rejected, future balance/label exclusion, duplicate-ID idempotency and conflicts.
PASS: same-seed generator produces identical bytes; artifact receipt written to reports/phase1-foundation.json.
```

The verification script's actual pytest subprocess is:
`python -m pytest ml_service/tests -q -o junit_family=legacy --junitxml=<temporary-path>/tests.xml`.
Test counts and parity evidence are parsed from JUnit, not manually assigned.
Report includes generated-data hash, source hash, feature-schema hash and actual
package/runtime versions. It intentionally contains no model-performance metric.

```text
# Working directory: ml_service
python -m simulation.generator --allow-synthetic --out ../data/generated/acceptance-a.json
python -m simulation.generator --allow-synthetic --out ../data/generated/acceptance-b.json
PASS: both emitted SHA-256 29c8264acfd5a3a0e14bb16fe92f68e867b69b7143abf6a447298668ae62168f.
python -m simulation.generator --out ../data/generated/refused.json
EXPECTED REFUSAL (exit 2): Synthetic generation requires explicit --allow-synthetic.
# Working directory: repository root
Get-FileHash data/generated/acceptance-a.json,data/generated/acceptance-b.json -Algorithm SHA256
PASS: identical hashes matching the generator receipt.
python scripts/download_data.py --dataset amlworld --variant HI-Small --license-acknowledged CDLA-Sharing-1.0
BLOCKED (exit 1): Kaggle credentials absent. No data substituted and no download receipt created.
git check-ignore data/generated/acceptance-a.json data/generated/acceptance-b.json
PASS: both generated datasets excluded from version control.
git diff --check
PASS: whitespace check clean (Git may warn about future LF/CRLF conversion).
```

Syntax check (no bytecode/model writes):

```powershell
python -c "import ast,pathlib; paths=list(pathlib.Path('ml_service/mulenet_core').glob('*.py'))+list(pathlib.Path('ml_service/simulation').glob('*.py'))+list(pathlib.Path('ml_service/tests').glob('test_*.py'))+[pathlib.Path(p) for p in ['ml_service/feature_service.py','ml_service/training/build_dataset.py','scripts/download_data.py','scripts/verify_data_foundation.py']]; [ast.parse(p.read_text(encoding='utf-8'), filename=str(p)) for p in paths]; print('PASS: syntax checked',len(paths),'new Python files')"
```

Output: `PASS: syntax checked 17 new Python files`.

Warnings disclosed: the installed Starlette TestClient warns that its httpx
transport is deprecated. The host's pyreadline3 destructor prints a Windows handle
error during interpreter shutdown; pytest and the verifier still return exit 0.
These are not represented as a clean supply-chain/security scan. Dependency locks,
clean-environment reproduction, full legacy regression tests and CI remain undone.

Acceptance: foundation checks pass; authorized dataset acquisition and migration
of legacy scoring/training/evaluation callers remain incomplete. Downloader
positive-path tests use a mocked CLI fixture, NOT an authenticated real download.
User explicitly said benchmark inputs will be provided later. The next model/
benchmark phase cannot earn acceptance without them. No full-phase/overall DOD
completion, main CI health, predictive performance or production safety is claimed.

Claims removed/downgraded: new simulator output is explicitly synthetic; PaySim
is documented as simulated, balance availability is time-bounded, and no direct
I4C/NCRP connection or economic benefit is claimed. Existing README claims are
unchanged and remain quarantined by the audit until the artifact-based rewrite.

Repeat-run report-byte check (exit 0):

```text
(Get-FileHash reports/phase1-foundation.json -Algorithm SHA256).Hash
python scripts/verify_data_foundation.py
(Get-FileHash reports/phase1-foundation.json -Algorithm SHA256).Hash
```

Both report hashes:
`9192ff06110df38ab8ec83164798b32463f847da5305784c3df1c3dfd524fa35`.
Both executions passed the entire foundation suite. No wall-clock timing or
temporary path is embedded in the receipt. Baseline source-quotation verification
was rerun and all audit quotations still resolve. No phase acceptance beyond
this documented reference-foundation scope is implied.
