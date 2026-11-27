# Definition of Done: Not Complete

Do not treat feature-foundation unit tests as production readiness. The work is
still implementing and verifying the remaining phases. Public benchmark inputs
have now been downloaded with supplier metadata/hash receipts; credentials are
no longer an acquisition blocker. The operator merged the published phase
checkpoints; hosted CI acceptance is not established.

- [ ] Clean-checkout setup/data/train/eval/bench/test/lint: explicit simulator data/train/eval and actual-network bench commands pass locally, along with Python/Java acceptance and core/policy coverage. Primary full-network evaluation, complete platform/UI lint and clean-checkout hosted acceptance remain unfinished.
- [x] Safe model loading and manifest/schema verification: enforced in the active service; legacy pickle sources/bundles retired. [Artifact tests](../reports/security-python-tests.json) and [unsafe-call gate](../reports/unsafe-paths.json) pass. Integrity hashes are not artifact publisher signatures.
- [ ] Complete leakage-audited benchmark results: simulated temporal/entity and PaySim temporal reports exist; full-network AMLworld remains unmeasured and bounded cohorts are explicitly not estimable.
- [ ] Real message-passing GNN, low-FPR ablation and latency evidence: GATv2/NeighborLoader, safe export, ablations and a measured model-only harness exist; full load/README gates remain.
- [x] Generated README metrics and local load percentiles: tables are rendered from JSON; [actual-network benchmark](../reports/latency-pipeline.json) measures individual ML HTTP and Kafka-producer-to-SSE requests under steady/burst load with bootstrap intervals. Local hot-account traffic is not deployment-scale capacity; the unselected neural path and separate component percentiles remain unmeasured.
- [x] Degradation, idempotency, DLQ and audit chain: [real-stack gate](../reports/platform-tests.json) passes against Kafka/Postgres/Redis/ML, including healthy scoring, duplicates, outage, release/expiry and integrity checks; small-fixture evidence, not a scalability certification.
- [ ] Authentication/secrets/supply-chain gates: negative and tenant-scoped SSE tests pass. Spring Enterprise patch access, vendor-unfixed Debian advisories and provider-credential revocation remain open. Expanded history scanning detects the previously missed legacy deployment credential. [Aggregate security gate](../reports/security-gate.json) intentionally fails; not production safe.
- [ ] Required threat/model/runbook/privacy documentation: research-scope documents exist; current architecture measurements and audit closure remain incomplete.

Available evidence: [audit](AUDIT.md), [architecture](ARCHITECTURE.md),
[execution log](CHANGELOG_AGENT.md), [decisions](DECISIONS.md),
[generated foundation receipt](../reports/phase1-foundation.json).

Additional evidence: [frozen evaluation repeatability](../reports/evaluation-reproducibility.json),
[measured evaluations and primary limitations](../reports/metrics.json),
[isolated locked-runtime tests](../reports/platform-python-tests.json),
[strict serving/registry tests](../reports/serving-tests.json),
[platform contract and limitations](PLATFORM_CONTRACT.md).
