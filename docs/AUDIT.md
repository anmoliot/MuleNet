# Evidence-Based Audit

Baseline: `85b10e6e5df87f6ce7f44bb2ea6e12e66d65cf8a` (origin/main).
The configured workspace was absent; a clean copy was cloned from the named
remote. Earlier local uncommitted files were not recovered. Scope: source,
configuration, migrations, tests, notebook source, tracked metrics/model metadata.
All findings are OPEN unless identified as a corrected suspicion. Static inspection
is not a passing runtime test. Historical numbers quoted here are disputed source
claims/configuration, not newly measured performance.

## Findings

P0: immediate exposure/unsafe operation. P1: substantial correctness/security risk.
P2: reproducibility/operability gap. Evidence is an exact source substring at the
specified line. Fix phase is planned work, not a completed remediation.

| ID | Severity | Finding / impact | File:line | Evidence | Fix Phase |
|---|---|---|---|---|---|
| A001 | P1 | Offline GNN training uses random tanh features and ridge W2, with no adjacency/message passing. | `ml_service/training/train_and_test.py:202` | `H = np.tanh(Xg @ W1)` | 2 |
| A002 | P1 | Two added columns (pr and bw), NOT all three, copy pass-through. deg is a distinct degree ratio. Corrected suspicion. | `ml_service/training/train_and_test.py:191` | `pr = (X[:, 4] * 300.0) / 300.0` | 1, 2 |
| A003 | P1 | Pass-through inverted: receiver-only sink scores one. Also repeated in preprocess.py. | `ml_service/training/train_and_test.py:107` | `pt_rate = min(total_recv / max(total_sent, 1.0), 1.0)` | 1 |
| A004 | P1 | Count entropy uses global normalization, not local amount-weighting. With unique originators it is determined by incoming count; actual dataset collinearity is unmeasured. | `ml_service/training/train_and_test.py:95` | `max_entropy = np.log2(max(df["nameOrig"].nunique(), 2))` | 1 |
| A005 | P1 | Labels and features use the same whole-input edges before random split, encoding later drainage rather than predicting future-only events. | `ml_service/training/train_and_test.py:73` | `dest_fraud = set(df.loc[df["isFraud"] == 1, "nameDest"])` | 1 |
| A006 | P1 | Raw edge sampling destroys connected transaction histories before account aggregation. | `ml_service/training/train_and_test.py:69` | `df = df.sample(max_rows, random_state=42)` | 1 |
| A007 | P1 | Threshold maximizes F1 using TEST labels, not VAL. | `ml_service/training/train_and_test.py:234` | `p = precision_score(y_test, hard, zero_division=0)` | 2, 3 |
| A008 | P1 | Latency is amortized batch duration, not single-row percentiles or end-to-end latency. | `ml_service/training/train_and_test.py:227` | `latency_ms = (time.perf_counter() - t0) * 1000 / len(X_test)` | 3 |
| A009 | P1 | IsolationForest evaluation discards continuous ranking through hard labels. Serving does use score_samples; paths differ. | `ml_service/training/train_and_test.py:285` | `iso_pred = iso_model.predict(X_test)` | 2 |
| A010 | P1 | Fixed contamination assumption rather than unsupervised ranking plus validation-only policy. | `ml_service/training/train_and_test.py:170` | `contamination=0.1` | 2 |
| A011 | P1 | Missing/failed real-data load silently changes experiment to synthetic without explicit opt-in. | `ml_service/training/train_and_test.py:133` | `X, y = _generate_training_data(n_samples=12000)` | 1, 2 |
| A012 | P1 | Missing XGBoost silently changes model family. | `ml_service/training/train_and_test.py:39` | `from sklearn.ensemble import GradientBoostingClassifier` | 2 |
| A013 | P0 | Pickle artifact loading can execute code; no hash/schema manifest verification precedes it. | `ml_service/ml_models.py:124` | `self.model = pickle.load(f)` | 2, 5 |
| A014 | P1 | Trainer imports generator/feature names from serving, not shared as-of feature computation. | `ml_service/training/train_and_test.py:26` | `_generate_training_data,` | 1 |
| A015 | P1 | Offline PaySim trainer log-transforms money but serving scales raw amounts; canonical preprocess is not invoked here. | `ml_service/ml_models.py:182` | `X_scaled = self.scaler.transform(X)` | 1, 2 |
| A016 | P1 | Offline tanh/ridge+bias artifacts served with bias truncation, ReLU, default random attention and neighbor aggregation. | `ml_service/ml_models.py:284` | `W2 = W2[:self.hidden_dim]` | 2 |
| A017 | P1 | NumPy serving path DOES perform neighbor aggregation. No PyG/NeighborLoader/exported temporal GNN was found. Corrected suspicion: not all GNN code lacks messages. | `ml_service/ml_models.py:485` | `X_agg[i] = 0.5 * X[i] + 0.5 * agg` | 2 |
| A018 | P1 | GNN serving uses batch-dependent money normalization; time decay also uses wall clock, not event as-of. | `ml_service/ml_models.py:541` | `col_max = X[:, col_idx].max()` | 1, 2 |
| A019 | P1 | Synthetic target-conditional feature sampling creates trivial separability, not history-derived topology validation. | `ml_service/ml_models.py:89` | `pass_through = min(0.6 + abs(rng.normal(0.2, 0.1)), 1.0)` | 1, 3 |
| A020 | P1 | README combines separate PaySim and synthetic cohorts, attributing synthetic FastPath scores to GNN+centrality. | `ml_service/training/metrics.json:94` | `"model_type": "GradientBoosting"` | 3, 8 |
| A021 | P1 | Perfect synthetic result stored by FastPath evaluation, not a graph ablation; matching JSON under trained_models. Producer inferred by schema, not reproduced. | `ml_service/training/metrics.json:4` | `"roc_auc": 1.0` | 3, 8 |
| A022 | P1 | Separate PaySim metadata lacks data hash, split indices, saved predictions and CIs. No producer found in tracked Python/notebook source. | `ml_service/trained_models/model_metadata.json:22` | `"pr_auc": 0.0407` | 3, 8 |
| A023 | P1 | Recovery claim is illustrative/self-seeded, not measured bank interception. DataSeeder implements one example, not the documented batch. | `backend/src/main/java/com/mulenet/api/config/DataSeeder.java:92` | `demo.setRecoveryEstimate(198000.0);` | 3, 8 |
| A024 | P1 | Registry hits are locally seeded and complaint counts simulated; optional AbuseIPDB lookup is not direct I4C/NCRP access. | `ml_service/external_intel.py:117` | `ncrp_complaints = 3  # simulated count` | 4, 8 |
| A025 | P1 | Claimed Platt calibration is fixed sigmoid, not fitted calibration; fusion weights hand-set, not learned stacking. | `ml_service/ml_models.py:740` | `scaled = 100.0 / (1.0 + math.exp(-0.08 * (raw_score - 45.0)))` | 2 |
| A026 | P1 | Merchant ensemble adds an extra rule-shaped uplift; no selection/ablation evidence. | `ml_service/agent_loop.py:96` | `+ pattern_score` | 2, 3 |
| A027 | P1 | Without truth, demo invents false positives and exposes numeric confusion/cost metrics. | `ml_service/agent_loop.py:162` | `fp = max(0, round(len(flagged) * 0.05))` | 3 |
| A028 | P1 | Cluster allocation precedes prevalence calculation; even zero ratio requests a positive and cashout nodes expand denominator. | `ml_service/razorpay_simulator.py:44` | `target_mules = max(1, int(n_beneficiaries * mule_ratio))` | 1 |
| A029 | P1 | Simple graph overwrites repeated account pairs; counters/edges diverge and global graph has no TTL/node cap. | `ml_service/graph_builder.py:165` | `GLOBAL_GRAPH.add_edge(` | 1, 4 |
| A030 | P1 | Base features include future/global edges and device/complaint degrees; only auxiliary windows filter time. | `ml_service/graph_builder.py:226` | `out_deg = G.out_degree(node)` | 1 |
| A031 | P1 | Historical queries can use current Redis aggregates without as-of/version check; outage changes implementation. | `ml_service/graph_builder.py:255` | `cached = REDIS_CONN.hgetall(f"features:{acct_id}")` | 1, 4 |
| A032 | P0 | ML verifier accepts any nonempty bearer text; no signature/issuer/audience/expiry/roles. | `ml_service/main.py:42` | `if not token:` | 5 |
| A033 | P0 | Analyze/predict/retrain/graph and SSE omit even that verifier; published ML port bypasses Spring. | `ml_service/main.py:74` | `def analyze_graph(request: IntakeRequest):` | 5 |
| A034 | P1 | Seed has no admin/demo-profile guard. Unauthenticated seed is NOT confirmed: both security chains require authentication by default. | `backend/src/main/java/com/mulenet/api/controller/DemoController.java:19` | `public ResponseEntity<?> seedDemo() {` | 5 |
| A035 | P1 | Application startup seeds demo cases/watchlists regardless of demo profile. | `backend/src/main/java/com/mulenet/api/config/DataSeeder.java:28` | `seedWatchlist();` | 5 |
| A036 | P0 | Committed default credentials; production randomization still logs generated secrets. | `backend/src/main/java/com/mulenet/api/config/DataInitializer.java:74` | `System.err.println("Generated secure bootstrap credential: " + username + " / " + passwordToUse);` | 5 |
| A037 | P1 | Public signing-key default accepted outside prod guard. Full history has NOT been scanned with gitleaks. | `backend/src/main/java/com/mulenet/api/config/JwtUtil.java:35` | `if (activeProfiles != null && activeProfiles.contains("prod")) {` | 5 |
| A038 | P1 | Spring SSE DOES have method role guards, but streams broadcast globally without tenant/assignment scope. | `backend/src/main/java/com/mulenet/api/service/NotificationService.java:153` | `for (SseEmitter emitter : streamEmitters) {` | 5 |
| A039 | P1 | Query-string JWT for Spring SSE can leak via access logs; ML SSE is unauthenticated. | `frontend/src/App.jsx:376` | `const url = `${API}/api/notifications/subscribe?token=${token}`;` | 5, 7 |
| A040 | P1 | Credentialed Spring CORS accepts all origin patterns. | `backend/src/main/java/com/mulenet/api/config/SecurityConfig.java:67` | `config.setAllowedOriginPatterns(Collections.singletonList("*"));` | 5 |
| A041 | P1 | Security chains use different property names and can overlap when only app.security.oauth2.enabled is configured. | `backend/src/main/java/com/mulenet/api/config/SecurityConfig.java:25` | `@ConditionalOnProperty(name = "OAUTH2_ENABLED", havingValue = "false", matchIfMissing = true)` | 5 |
| A042 | P1 | Failed Kafka processing acknowledged with no DLQ; persistence/decisions lack transactional deduplication. | `backend/src/main/java/com/mulenet/api/kafka/KafkaConsumerService.java:112` | `acknowledgment.acknowledge();` | 4 |
| A043 | P1 | Java/Python consumers use different topics; Python worker not launched by ML Docker CMD. | `backend/src/main/java/com/mulenet/api/kafka/KafkaConsumerService.java:50` | `@KafkaListener(topics = "mule-events", groupId = "mulenet-backend-group")` | 4 |
| A044 | P1 | Fixed long retries, no circuit breaker/degraded policy. Compose ML_SERVICE_URL differs from app.ml-service.url read here. | `backend/src/main/java/com/mulenet/api/service/MlService.java:66` | `throw new RuntimeException("ML service unavailable after retries", e);` | 4 |
| A045 | P1 | Auto-executable freeze recommendation lacks max hold/release scheduler/appeal/cost validation; not a verified bank intervention. | `backend/src/main/java/com/mulenet/api/service/PolicyEngine.java:142` | `decision.put("auto_executable", score >= freezeThreshold);` | 4 |
| A046 | P1 | Thresholds mutable without versions/order validation; SSE separately duplicates fixed thresholds. | `backend/src/main/java/com/mulenet/api/service/PolicyEngine.java:246` | `this.freezeThreshold = newThresholds.get("freeze_threshold");` | 4 |
| A047 | P1 | Closed/frozen feedback treated as fraud for every case account; active objects retrained without adjudication/poisoning guard. | `ml_service/celery_app.py:52` | `label = 1 if status in ["FROZEN", "CLOSED"] else 0` | 4 |
| A048 | P1 | Unbounded process-local audit map, not durable/hash-chained. DB AuditLog also has no chain fields. | `ml_service/main.py:53` | `AUDIT_RUNS = {}` | 4, 5 |
| A049 | P1 | Raw account/device identifiers stored/broadcast and raw Kafka payload logged; no tokenization boundary here. | `backend/src/main/java/com/mulenet/api/kafka/KafkaConsumerService.java:53` | `logger.info("Received Kafka message on topic mule-events: {}", record.value());` | 5 |
| A050 | P2 | Python dependency ranges, no torch/PyG; npm lock and Maven BOM do exist. Not all dependencies are wholly unpinned. | `ml_service/requirements.txt:1` | `fastapi>=0.110.0` | 5, 6 |
| A051 | P2 | Zookeeper/plaintext Kafka, host-published stores, root-default ML image/fixed sleep; no verified health-gated stack. | `docker-compose.yml:36` | `KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181` | 4, 5, 6 |
| A052 | P2 | Celery handles retraining, Kafka ingestion: distinct functions, not automatically duplicate queues. Tasks currently carry user Authorization. | `ml_service/celery_app.py:25` | `def retrain_models_task(self, authorization_header):` | 4 |
| A053 | P2 | Existing CI lacks eval reports, coverage/security/image/stack gates; second lint pass is advisory. | `.github/workflows/python-package-conda.yml:34` | `flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics` | 6 |
| A054 | P1 | External AML reservoir sample destroys topology, ignores time/bank namespaces and labels feature edges. IBM data are simulated, not real bank outcomes. | `ml_service/external_benchmark.py:102` | `reservoir[j] = row` | 1, 3 |
| A055 | P1 | ML SSE generates its own anomaly flag/features and score bonus; not persisted live Kafka decisions. | `ml_service/main.py:513` | `raw_score = fp_prob * 45 + ad_prob * 35 + (30 if is_anomaly else 5)` | 2, 7, 8 |
| A056 | P2 | Retraining driver imports missing tracked modules; advertised routine cannot run as shipped. | `ml_service/training/retrain_models.py:8` | `from train_xgboost import main as train_xgboost` | 2, 6 |
| A057 | P1 | Separate cold-start monitor advice does not override main pipeline's scored action. | `ml_service/agent_loop.py:202` | `"action": "MONITOR_ONLY",` | 4 |
| A058 | P1 | Merchant demo uses unprefixed nodes but analytics filters for account: nodes, losing rings/components. | `ml_service/graph_analytics.py:141` | `and u.startswith("account:") and v.startswith("account:")` | 1, 7 |
| A059 | P2 | Optional SHAP/fallback attribution not always SHAP; FastPath TreeExplainer uses raw X instead of scaled input. | `ml_service/ml_models.py:246` | `shap_vals = explainer.shap_values(X)` | 2, 7 |
| A060 | P1 | Timestamp is a string; invalid dates become wall-clock now. Demo counts/thresholds and batch size unbounded. | `ml_service/graph_builder.py:99` | `return datetime.datetime.utcnow()` | 1, 5 |

## Metric Lineage

`training/train_and_test.py::main -> evaluate` writes
`ml_service/training/metrics.json`. That report declares SYNTHETIC and
GradientBoosting; values match `trained_models/metrics.json`. It does not evaluate
GraphNeuralScorer. README's synthetic topology/GNN attribution is unsupported.
Historical script provenance is inferred from matching structure; no run was
reproduced and authorship cannot be proven from the JSON alone.

`trained_models/model_metadata.json` separately declares PaySim/XGBoost. Neither
report includes saved predictions, data hash, split indices, CI, or a reproducible
environment. No producer for the separate PaySim metadata was found in tracked
Python/notebook source. The README combines distinct cohorts, not one experiment.
Do not deserialize the legacy pickles to investigate their provenance.

The reported latency is amortized synthetic batch timing, not a single-row,
HTTP, or Kafka-to-SSE benchmark. Fast/deep latency bounds lack harness evidence.
METRICS_REPORT calls PaySim real-world and claims temporal separation; inspected
training code aggregates the entire input then randomly splits accounts. This
is missing/countervailing evidence, not proof about every historical experiment.

Recovery figures in README/METRICS_REPORT are illustrative. DataSeeder creates a
single example with fixed scores and an estimated recovery; it cannot reproduce
the documented batch or prove funds were intercepted or returned.

## GNN Location

The offline ridge trainer is at `training/train_and_test.py::train_gnn_weights`.
A different NumPy neighbor-aggregation implementation exists in
`ml_models.py::GraphNeuralScorer`, with synthetic initialization/training when
artifacts are absent. Its `_message_pass` reads actual neighbors. Offline and
serving forward passes/transforms disagree; the artifact bias is discarded and
default attention is random. No PyG GAT/GINE/NeighborLoader implementation,
time-isolated inductive benchmark, export, or GNN ablation was found. Neither
absence of all message passing nor a validated temporal GNN is a justified claim.

## Verification Limits and Acceptance

No legacy model loading/training, database mutation, demo seeding or freeze was
invoked. Security observations require negative integration tests. Full-history
gitleaks, dependency/image scans, license review, dataset evaluation and latency
remain unverified. No dataset is included. Docker CLI/make/uv/gitleaks were not
found on PATH and default Java is older than the project target.

Acceptance: every table row resolves to an actual file:line quotation; docs-only
diff; architecture includes competing event paths and unmeasured latency remains
blank. Execution evidence belongs in CHANGELOG_AGENT.md, not a performance claim.
