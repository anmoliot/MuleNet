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

## Phase 2: Candidate Models and Public Data Acquisition

Branch: phase-2-models. Changed files: new mulenet_core/artifacts.py and models.py;
training/train_tabular.py, train_gnn.py, experiment.py; explain.py and drift.py;
model/downloader tests; public downloader mode; bounded graph-stat caching;
scripts/record_tests.py; dataset receipts; data notes and decisions. Model binaries
and raw data are ignored. The active legacy serving path is not yet migrated.

Commands actually executed:

```text
python -m venv .venv --system-site-packages
.venv\Scripts\python.exe -m pip install uv skops torch-geometric shap ruff mypy types-networkx pytest-cov pip-audit
.venv\Scripts\python.exe -m pip install --only-binary=:all: pyg_lib torch_scatter torch_sparse -f https://data.pyg.org/whl/torch-2.12.0+cpu.html
PASS: project-local dependencies installed; inherited host packages remain a reproducibility limitation until the locked setup phase.
```

The direct NeighborLoader probe produced a sampled PyG Data batch, not a stub.
The public notebook API was read without executing notebook cells; its random
split and post-transfer balance features are documented in data/README.md.
Public supplier metadata confirmed licenses and versioned anonymous download URLs.

```text
.venv\Scripts\python.exe scripts/download_data.py --dataset paysim --variant default --license-acknowledged CC-BY-SA-4.0 --public
.venv\Scripts\python.exe scripts/download_data.py --dataset amlworld --variant HI-Small --license-acknowledged CDLA-Sharing-1.0 --public
.venv\Scripts\python.exe scripts/download_data.py --dataset amlworld --variant LI-Small --license-acknowledged CDLA-Sharing-1.0 --public
PASS: requested files downloaded; supplier metadata, version, license and content hashes recorded in reports/data-*.json. No raw data committed.
.venv\Scripts\python.exe -m pytest ml_service/tests/test_models.py ml_service/tests/test_data_download.py -q
PASS: model/loader checks after fixing two failures described below.
.venv\Scripts\python.exe scripts/record_tests.py --phase models ml_service/tests
PASS: measured outcomes are in reports/models-tests.json; no skipped tests accepted as passing.
```

From ml_service, explicit demo training:

```text
..\.venv\Scripts\python.exe -m training.experiment --dataset sim --data ../data/generated/training-demo.json --split temporal --out ../artifacts/demo-temporal-v2 --allow-synthetic --epochs 20
..\.venv\Scripts\python.exe -m training.experiment --dataset sim --data ../data/generated/training-demo.json --split entity --out ../artifacts/demo-entity --allow-synthetic --epochs 20
PASS: actual XGBoost + edge-aware GATv2/JumpingKnowledge models trained; early stopping, calibration/thresholds and OOF meta fitting use validation only.
```

The input was generated through the repository generator with seed/configuration
recorded in its JSON, using a small development fixture. Training reports are
script-written reports/training-sim-*.json, not external benchmark claims.
Both runs chose tabular-plus-graph as the default deep path on validation; no
test-set comparison was used for that choice. Final low-FPR test performance is
pending Phase 3, not inferred from training or validation.

Failures found and fixed: NeighborLoader attempted to index string account IDs;
tensor-only training batches now keep IDs outside the sampler. skops correctly
rejected sklearn.tree._tree.Tree; only that expected tree type and the reviewed
isotonic interpolator are explicitly permitted, never the entire unknown-type
list. Integrity/schema tests reject tampered artifacts before parser invocation.
Dynamic empty-edge inference, TreeSHAP, actual GNNExplainer edge masks, cold
reference features and drift-shift tests ran. Initial ruff findings are not yet
a passing lint gate; formatting/strict typing are part of the CI phase.

Known warnings: inherited requests dependency mismatch; PyTorch TorchScript and
PyG annotation deprecations; the host TestClient transport deprecation. These are
disclosed, not suppressed or represented as a clean supply-chain scan.

Acceptance scope: candidate training, export/reload, explicit data opt-in and
artifact rejection checks pass. Full report/ablation/robustness acceptance is
performed in Phase 3; production service replacement and old pickle retirement
remain required. Claims downgraded: a real GNN is now implemented, but it is not
assumed to improve results or earn serving latency. Dataset acquisition no longer
depends on missing credentials; every downloaded benchmark is still simulated.

After adding explicit manifest metrics-file/hash consistency, both training
commands were repeated into new immutable directories demo-temporal-v3 and
demo-entity-v2. Those candidates replace the earlier development bundles for
subsequent evaluation; no manifest fields or model metrics were hand-edited.

## Phase 3: Evaluation Evidence (In Progress)

Changed: deterministic bootstrap metrics, frozen-candidate evaluation, robustness,
terminal-credit lead-time diagnostics, calibrated probability validation, full
PaySim temporal evaluation, source inventories and label-independent AML cohorts.
All report values are written by scripts, including non-estimability diagnostics.

Commands executed from ml_service unless prefixed scripts/:

```text
python ../scripts/profile_datasets.py --help
python -m eval.run_eval --dataset sim --split temporal --data ../data/generated/training-demo.json --models ../artifacts/demo-temporal-v3 --out ../reports/metrics-sim-temporal.json --allow-synthetic
python -m eval.run_eval --dataset sim --split entity --data ../data/generated/training-demo.json --models ../artifacts/demo-entity-v2 --out ../reports/metrics-sim-entity.json --allow-synthetic
python -m eval.paysim --data ../data/raw/paysim/PS_20174392719_1491204439457_log.csv --models ../artifacts/paysim-temporal-v2 --train
python -m eval.paysim --data ../data/raw/paysim/PS_20174392719_1491204439457_log.csv --models ../artifacts/paysim-temporal-v2
python -m eval.amlworld --variant HI-Small
python -m eval.amlworld --variant LI-Small
python scripts/aggregate_reports.py
python scripts/record_tests.py --phase evaluation ml_service/tests
python scripts/bench_latency.py --mode model --models artifacts/demo-temporal-v3 --allow-synthetic
```

Output summary: candidate evaluations and full PaySim temporal evaluation exit
successfully; reports contain bootstrap confidence intervals and scope warnings.
AML reports explicitly say not_estimable with null performance, not fabricated
AUCs. Aggregator retains production_approved=false. Test receipt is
reports/evaluation-tests.json; latency receipt reports individual calls, not
batch-time/row. It explicitly excludes features, HTTP, Kafka, policy and SSE.

Initial full PaySim evaluation failed on isotonic interpolation outside the
unit interval; a shared, tested roundoff-only bound fixes representation error.
The report includes correction diagnostics. Larger invalid probabilities fail.
Expensive initial AML feature builds were cancelled, not called passing runs;
label-only preflight now diagnoses insufficient classes before model fitting.

Acceptance remains OPEN: full connected-network AMLworld evaluation and complete
Kafka-to-SSE latency are not implemented. Frozen-report repeatability is checked
separately; a model-only latency result is never described as end-to-end.
Claims downgraded: the supplied PaySim notebook is not topology evidence;
terminal-credit coverage is not money recovered; a clean bootstrap interval at
zero false alarms does not prove zero population risk (exact intervals included).

```text
python scripts/verify_evaluation.py
PASS: reports/evaluation-reproducibility.json records byte-identical temporal and entity numerical reports.
```

Visual check: the generated PaySim pre-transfer PR plot is nonblank, axes are
labelled and fit without overlap. This is report QA, not a performance assertion.
The supplied older attachment requested preserving legacy components; the newer
phased security/evaluation specification supersedes those preservation requests
where they conflict with safe model serving and platform hardening.

## Phase 4: Tested Platform Checkpoint

Changed: strict internal scoring API and exported OpenAPI, generated Java client,
deadline-isolated GNN fallback, content-addressed Redis snapshots, Spring JDBC
ledger/decisions, versioned policy, durable outbox, keyed KRaft ingestion, encrypted
DLQ/replay, review workflow/expiry, audit chain, tokenization/encryption, scoped
SSE and explicit per-install demo authentication. Legacy controllers, consumers,
initializers and security chains are excluded from the default platform profile.
Deployment support now uses non-root service images, separate migration/runtime
DB credentials and internal-only Redis/ML/Kafka. See PLATFORM_CONTRACT.md for limits.

```text
python scripts/record_tests.py --phase serving ml_service/tests/test_serving.py
PASS: reports/serving-tests.json; actual artifact-backed HTTP tests, tenant/scope rejection, hard-process timeout, registry shadow/canary/rollback.
uv run --isolated --frozen --all-groups python scripts/record_tests.py --phase platform-python ml_service/tests
PASS: reports/platform-python-tests.json; no inherited packages or skipped tests, source unchanged during the run.
python scripts/record_tests.py --phase feedback ml_service/tests/test_feedback.py
PASS: reports/feedback-tests.json; disagreement, missing independent review and immature adjudication quarantined.
python scripts/record_tests.py --phase platform-tools ml_service/tests/test_platform_tools.py
PASS: reports/platform-tools-tests.json; exclusive unique secret generation, audit tamper/order/truncation rejection.
python scripts/export_openapi.py --models artifacts/demo-temporal-v3 --allow-synthetic
PASS: actual application schema exported to contracts/ml-openapi.json; generated sources are not edited.
python scripts/record_maven_tests.py --wsl
PASS: reports/platform-tests.json; BUILD SUCCESS, no failed/skipped checks, source unchanged.
sh scripts/bootstrap_secrets.sh --demo --out .tools/bootstrap-smoke.env
PASS: wrapper executed without overwriting installation secrets or printing passwords.
```

The Maven recorder executes Maven with Java from the installed WSL runtime and
derives outcomes only from newly written Surefire XML. It does not count stale
test files after a compilation failure. Its integration scenario runs actual
Kafka, PostgreSQL, Redis and artifact-backed ML containers: healthy decisions,
duplicate/conflicting delivery, encrypted DLQ, injected ML outage, null degraded
probability, authorization, manual/automatic release, cross-tenant reads and
immutable audit/policy storage all assert successfully. The API client regression
also verifies long timestamps and nonempty strict request serialization.

Executed registry commands from ml_service, all with explicit --allow-synthetic:

```text
python -m model_registry init --root ../artifacts --version demo-temporal-v3 --allow-synthetic
python -m model_registry shadow --root ../artifacts --version demo-entity-v2 --allow-synthetic
python -m model_registry canary --root ../artifacts --version demo-entity-v2 --percentage 25 --allow-synthetic
python -m model_registry promote --root ../artifacts --version demo-entity-v2 --allow-synthetic
python -m model_registry rollback --root ../artifacts --allow-synthetic
PASS: active pointer restored to demo-temporal-v3; shadow does not affect policy.
```

Failures found, not hidden: the previous Mockito agent could not self-attach;
subclass mocks expose two existing fixture errors, repaired in the tests. Docker
rejected the old Testcontainers API client; a compatible release fixes it without
weakening Docker. Real scoring then exposed the old generator's empty-map
serialization bug. Official normalization and a compatible Spring patch fix it;
the closed server schemas remain strict. A premature manual Spring shutdown
caused teardown failure and was removed. A killed GNN could leave a queue feeder
blocked; cancellation now permits clean process exit. The log recorder's Windows
text decoding failure is fixed with explicit UTF-8, not by dropping failed tests.

Acceptance scope: the real-stack core replay/degradation gate passes. This is not
completion of every platform requirement: large-network adjacency scalability,
automatic verified-evidence feedback retraining and multi-version neural rollout
remain open. Case adjudication is quality-gated but never silently converted to
transaction truth. India signals unsupported by the schema are not invented.
Claims downgraded: no bank freeze execution, regulatory certification, actual
government watchlist access, exactly-once distributed transport or production
readiness. Container rebuild and broader security/CI/UI checks continue next.

## Phase 5: Security Checkpoint, Acceptance Still Open

Changed: removed the retired Java/ML execution paths, pickle bundles and unpinned
legacy installer files; preserved historical DB migrations but revoked runtime
access to legacy tables. Added purpose-separated service/ingestion/SSE signing,
strict JSON/input limits, bounded rate limits, encrypted bounded DLQ handling,
OIDC transport validation, admin-only tenant profile configuration and positive
tenant-scoped SSE assertions. Secrets are exclusive per-install values and never
printed. Added threat/privacy/setup notes, history triage, dependency/image scan
receipts, a fail-closed aggregate gate, pinned security workflow actions and
dependency-update configuration. The README default credential was removed.

Executed commands below use the clean uv-created runtime under .tools/runtime on
Windows; the Java recorder uses the installed WSL Java/Maven/Docker environment.

```text
uv lock
PASS: lock resolves the pinned scientific stack for the updated Python maintenance release.
UV_PROJECT_ENVIRONMENT=.tools/runtime uv sync --frozen --all-groups
PASS: clean runtime created without inherited system site packages.
python scripts/record_tests.py --phase security-python
PASS: reports/security-python-tests.json; no failures/skips and source/lock unchanged during the final run.
python scripts/record_maven_tests.py --wsl
PASS: reports/platform-tests.json; BUILD SUCCESS, actual patched ML container, no failed/skipped cases, source unchanged.
python scripts/configure_keycloak.py
PASS: reports/keycloak-configuration.json; admin-only tenant edit and disabled unmanaged attributes read back from the local running identity provider; no users created.
python scripts/audit_python.py --uv .venv/Scripts/uv.exe
PASS: reports/python-security.json; no known runtime/upstream-mapped advisories and no unhandled skipped packages.
npm ci --ignore-scripts --no-fund --no-audit
npm update --save --save-exact --ignore-scripts --no-fund --no-audit
PASS: exact direct dependency pins and refreshed lockfile installed.
python scripts/audit_frontend.py
PASS: reports/npm-audit.json; no advisories after compatible updates.
npm run build
PASS: production bundle built; existing size/Tailwind/config warnings remain for frontend work.
python scripts/check_unsafe_paths.py
PASS: reports/unsafe-paths.json; no forbidden deserialization calls in current Python source.
docker run --rm -v "$PWD:/repo:ro" -v "$PWD/reports:/reports" zricethezav/gitleaks:v8.30.1 git /repo --log-opts=--all --redact --report-format json --report-path /reports/gitleaks-history.json
FINDINGS: historical public signing defaults and generated source checksum matches; raw report redacted.
python scripts/triage_secrets.py
PASS: no untriaged historical findings; external installation credential rotation remains unverified.
mvn -B -ntp cyclonedx:makeAggregateBom
PASS: reports/sbom-backend.json generated and validated from the Maven dependency graph.
docker compose build backend ml_service
PASS: updated Python/OS runtime image and backend image built; unused global pip removed.
trivy image --timeout 30m --quiet --scanners vuln --format json --output reports/trivy-ml.json --exit-code 1 mulenet/ml:local
FAIL: remaining vendor-unfixed Debian advisories; no available fixes or Python-package findings remain in that scan. No severity filters or ignore list used.
python scripts/security_gate.py
FAIL: reports/security-gate.json honestly retains unfinished or failed scan gates. This is not full Phase 5 acceptance.
```

Failures investigated: Keycloak rejects a literal DISABLED unmanaged-attribute
enum; its actual API requires null, verified by read-back and a regression test.
Intermediate test runs had passing assertions but their receipts rejected source
edits made during execution; only the final unchanged-snapshot results count.
The first backend Trivy run timed out downloading its Java database; a bounded
longer retry uses the completed cache. OWASP's newer scanner had an anonymous-NVD
key regression; a compatible pinned release was used without invented credentials.
Initial Python/frontend scans found vulnerable pins. Compatible fixed releases,
official matching sampler wheels and actual model/export tests address those
findings; CPU wheel advisory mappings are explicit rather than silent skips.

Claims not made: clean image scan, hosted CI green, complete risk remediation,
remote credential rotation, production compliance or full project completion.
Remaining distribution advisories are open in SECURITY_EXCEPTIONS.md, not waived.
The local Keycloak verification service was stopped after its check completed.

Final Java scan follow-up: `mvn dependency-check:check` completed using the cached
database and failed with actual findings. Compatible explicit patch overrides
were applied for Jackson, Tomcat, PostgreSQL, Log4j and Kafka compression
libraries; the Alpine image packages were upgraded. The subsequent dependency
scan reports only Spring Framework/Security findings. The operator confirmed
that authorized enterprise repository access will be configured locally. Until
then, no corresponding finding is suppressed and Phase 5 is not declared done.
The SBOM goal is run separately because Maven correctly stops after the failed
vulnerability goal. A regenerated image scan and integration checks verify the
patched dependency graph; their generated receipts are the acceptance evidence.

Publication checkpoint requested by the operator:

```text
trivy image --timeout 30m --scanners vuln --format json --output reports/trivy-backend.json --exit-code 1 mulenet/backend:local
FAIL: completed scan; remaining Java findings concern spring-webmvc. The Alpine result has no listed vulnerabilities.
python scripts/security_gate.py
FAIL: Python, npm, unsafe-path, secret-triage and unchanged-source test receipts pass; OWASP and both container gates remain failed.
git diff --cached --check
PASS: no staged whitespace errors. Staged path review excludes local secrets, raw data, model artifacts and tool environments.
```

This is a publishable research checkpoint on the phase branch, not a declaration
of security acceptance or production readiness. Main is not merged or modified.

Pre-push verification found generated source checksums and the official Python
image's public signing-key fingerprint, not a new installation secret. The
fingerprint classification checks exact parsed metadata and has a negative test.
`python -m pytest ml_service/tests/test_security_tools.py -q` passed; running
`scripts/triage_secrets.py` on the full-history pre-push report then returned no
untriaged findings. Historical public defaults remain disclosed and require
rotation in any old installation. Local raw scanner output is redacted.
