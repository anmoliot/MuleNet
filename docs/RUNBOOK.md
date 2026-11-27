# Research Runbook

## Installation Boundary

This is not a production deployment guide. Read SECURITY_SETUP.md and
SECURITY_EXCEPTIONS.md first. Resolve credentials and vendor findings before
considering live deployment. Never use real customer data in this installation.
The retired Render file and Windows launcher must not be reused.

Use the locked environment and generated per-install secrets. Bootstrap preserves
existing secrets unless its documented upgrade mode is explicitly selected.
Restrict .env permissions; never paste its contents into logs or issues.

## Verify

```sh
uv sync --frozen --all-groups
uv run --frozen --all-groups python scripts/record_tests.py --phase local
uv run --frozen --all-groups python scripts/eval_smoke.py --allow-synthetic
uv run --frozen --all-groups python scripts/check_unsafe_paths.py
uv run --frozen --all-groups python scripts/render_readme_metrics.py --check
```

The Java test recorder requires Docker, Maven, Java and the locally built ML
image. Use --wsl only on Windows with the documented WSL toolchain. Mocked unit
tests do not establish running full-stack acceptance.

## Models and Rollback

### Drift Reference Upgrade

New serving bundles require drift-reference.json, included in the manifest hash
checks. Missing, tampered or schema-mismatched references fail loading, including
on the explicit demo path. Do not invent a baseline or edit a manifest to make an
old bundle appear compatible. Retrain into a new immutable version and evaluate
it before registry publication. Keep old artifacts/configuration for historical
reproduction with their matching code, not rollback into an incompatible runtime.

The continuation's evaluated examples are under artifacts/repro-phase6-drift-*
and a separate local artifacts/drift-registry. Originals were not overwritten.
Set MULENET_REGISTRY_ROOT to that evaluated compatible registry when using Compose;
the default still points to the existing artifacts directory, not an automatic
migration. The registry's registry.json, not MULENET_ACTIVE_MODEL bootstrap
metadata, selects the active candidate. An old root pointer is not silently repaired.

```sh
python scripts/verify_drift.py --models artifacts/repro-phase6-drift-sim-temporal --allow-synthetic
python scripts/verify_evaluation.py --run-id repro-phase6-drift --allow-synthetic
```

The first command writes a constructed replay/shift probe to
reports/drift-validation.json. It is not a live false-alarm or fraud-effectiveness
measurement. The second checks frozen numerical evaluation bytes within the named
run, without replacing published benchmark reports. Run probes sequentially when
they verify immutable artifact checksums; evaluation re-seals its evidence manifest.

### Live Drift Signals

The signed, metrics-scoped ML endpoint exports PSI, KS, KS p-values, observation
count, readiness and review-required signals for the token's tenant only. Process
operational counters remain global to privileged service monitoring; drift windows
do not aggregate tenants. No tenant/account identifier is used as a drift label.
Model and reference hashes distinguish changed baselines even if weights match.

Default live windows retain a bounded observation count and expire samples by a
monotonic age limit. Expiry is applied on collection; it is not a scheduled privacy
erasure guarantee. The implementation caps total window keys and explicitly counts
evictions. Restarts lose these in-memory windows, so readiness must build again.
With insufficient or expired observations, no PSI/KS or review verdict is emitted;
absence is not a healthy/no-drift result. Alert rules must gate on readiness.

Reference rows and score inputs come only from TRAIN. Score references use the
fitted/calibrated model on those rows, so they can differ from validation and
deployment distributions. The default PSI/KS review thresholds are monitoring
heuristics, not validated fraud or customer-harm operating points. Correlated
requests, many feature comparisons and small samples can produce misleading flags.
References contain derived features, not account identifiers, but remain sensitive
model data: do not commit artifacts or expose the reference arrays via metrics.

On review_required, check completeness, ingestion/source changes, model version and
reference hash first. Obtain independently adjudicated labels and apply existing
feedback-quality filters before retraining. Evaluate on held-out splits, shadow
the candidate and require approval before promotion. Do not automatically change
thresholds, hold customers, relabel decisions or promote weights from this signal.

The reproduction entry point has no default dataset. The following explicitly
simulated research run creates fresh temporal and entity-disjoint candidates:

```sh
make setup
make DATASET=sim ALLOW_SYNTHETIC=1 RUN_ID=research-run data train eval
```

The input generator is seeded and existing differing input is never replaced.
Training refuses to overwrite candidate weights; choose a new RUN_ID for another
training run. Evaluation can repeat against frozen candidates and writes under
reports/runs, leaving published benchmark evidence unchanged. This is not the
complete clean-checkout acceptance command or a working frontend demo.

`make DATASET=paysim data` and `make DATASET=amlworld data` verify local raw data
and supplier metadata against their receipts. They do not silently download or
accept licenses. Missing inputs require the documented download_data.py workflow
and explicit supplier-license acknowledgment. PaySim train/eval uses its separate
transaction protocol. AMLworld train/eval refuses to substitute bounded cohorts
for the currently unimplemented full-network evaluation.

`make test` executes Python and Java acceptance checks. On the Windows/WSL setup,
pass `JAVA_TEST_FLAGS=--wsl` when invoking the Windows Python runtime. Java policy
line and branch coverage are gated; this is not a claim of complete backend
coverage. Integration tests require a verified test-model directory, selected
with MULENET_TEST_MODEL_DIR relative to backend, and an actual local ML image.

Train into a new immutable directory. Require held-out evaluation, manifest
verification and schema parity before registry publication. From ml_service,
`python -m model_registry --help` describes init, shadow, canary, promote and
rollback. Synthetic candidates require explicit opt-in. Preserve previous
weights and evidence. Rollback changes selection, not historical decisions or
audit entries. Feedback filtering does not replace retraining approval.

## Incidents

### Local Latency Measurements

```sh
make ALLOW_SYNTHETIC=1 bench
```

This starts an ephemeral Kafka/Postgres/Redis/ML Testcontainers stack and a real
HTTP backend. Select the test model with MULENET_TEST_MODEL_DIR relative to the
backend directory; the image must already exist. Windows/WSL uses
JAVA_TEST_FLAGS=--wsl with the Windows Python runtime. The equivalent entry point
is scripts/bench_latency.py --mode pipeline --allow-synthetic, with optional --wsl.

reports/latency-pipeline.json records raw per-request samples, bootstrap intervals,
model/schema/image identities and exact boundaries. The hot-account workload is
closed-loop; generator-queue time, ingress REST/outbox and external networks are
not included in Kafka-to-SSE timing. Both committed account decisions must arrive
over HTTP SSE, without degraded scoring. ML HTTP includes cache/feature/model
execution and client parsing; snapshot preparation is outside that boundary.
Token creation is included in the HTTP measurement. The default graph-tabular
path is measured, not the unselected GNN. This is not a bank deployment SLO.

The benchmark refreshes short-lived SSE credentials and resumes by cursor. It
rejects missing, failed or degraded runs; it does not reuse earlier measurements.
Stage Prometheus histograms use only bounded stage/outcome labels. Backend JSON
logs carry correlation IDs during ML processing without logging event bodies or
credentials. A production collector/dashboard and complete OpenTelemetry traces
are still pending; the timer instrumentation alone does not complete that work.

Stop ingestion when authenticity or tenant isolation is doubtful. Preserve the
ledger, append-only audit chain and trusted external audit head. Revoke leaked
provider credentials at the provider; rotate affected installation keys and
sessions and prove old tokens fail. Source deletion is not credential revocation.
Git history is not rewritten automatically.

ML outages must produce explicit degraded decisions and internal SOFT_HOLD
review, not fabricated scores. Review expiry/release and audit every override.
Replay a DLQ item only after fixing its cause and checking its original identity.
Deduplication does not authorize changing a transaction.

## Remaining Operations Work

Full Compose/UI smoke acceptance, cross-stage traces, live load measurement,
retention/erasure, authenticated metrics collection and complete retraining
approval remain unfinished. Follow DOD_CHECKLIST.md, not the existence of this
document, when assessing readiness.
