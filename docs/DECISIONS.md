# Decisions

## ADR-000: Audit Before Modification
Status: Accepted for this execution.
Context: Repository claims are not tied to reproducible experiments.
Decision: Preserve the baseline and quote source evidence; do not load its pickles.
Consequence: Historical numbers are unverified claims, not baseline measurements.

## ADR-001: Recover Absent Workspace
Status: Accepted for this execution.
Context: The configured directory was absent and the original local state unavailable.
Decision: Clone the user-named GitHub remote, record its SHA, create a phase branch.
Consequence: No assertion is made that earlier uncommitted files were preserved.

## ADR-002: No Main Mutation Before Acceptance
Status: Accepted for this execution.
Context: The user requires separate phase branches/commits and a green main.
Decision: Keep main unchanged; layer each new phase branch on its accepted predecessor.
Consequence: Existing main CI health is unknown; phase acceptance is not main CI proof.

## ADR-003: Correct Suspicions, Do Not Amplify Them
Status: Accepted for this execution.
Context: Some requested audit suspicions differ from inspected source.
Decision: Record partial defenses, distinct metric cohorts and NumPy message passing.
Consequence: Seed authentication and entropy collinearity require qualified findings.

## ADR-004: Shared Reference Semantics Before Optimizations
Status: Accepted for the data foundation.
Context: Legacy train/serve features disagree and include future edges.
Decision: One strict event-time extractor; isolate entities before materialization.
Consequence: Large graph budgets fail explicitly; optimized Redis storage is later work.

## ADR-005: Quarantine Legacy Model Interfaces
Status: Accepted for the staged migration.
Context: Existing pickle models cannot consume the new feature schema safely.
Decision: Test a feature-only API and batch adapter; do not silently project into old models.
Consequence: Legacy application paths remain unsafe/unmigrated until Phase 2 replacement.

## ADR-006: Do Not Substitute Data for Blocked Benchmarks
Status: Superseded for acquisition by ADR-008; still prohibits substituted benchmark claims.
Context: CSVs/credentials are absent; user said they will provide inputs later.
Decision: Finish isolated foundation checks; do not replace primary benchmark evaluation with demo claims.
Consequence: Model/benchmark phases and overall acceptance remain incomplete.

## ADR-007: Balance and Clock Semantics
Status: Accepted for reference feature extraction.
Context: PaySim balances may describe outcomes; AMLworld clocks have no explicit timezone.
Decision: Use past-event balances only; treat simulation timestamps as a documented UTC clock convention.
Consequence: No current-transaction balance leakage or claim of real-world temporal availability.

## ADR-008: Public Versioned Benchmark Acquisition
Status: Accepted after successful supplier API/license checks and downloads.
Context: Public endpoints make account credentials unnecessary for the requested files.
Decision: Explicit public mode checks terms/visibility, pins provider versions and hashes bytes.
Consequence: Acquisition blocker is removed; data remain local and evaluation still must run.

## ADR-009: Safe Formats and Validation-Only Model Selection
Status: Accepted for candidate training; serving migration remains a later phase.
Context: Baseline pickles and hand-weighted pseudo-GNN cannot establish trustworthy scores.
Decision: Native XGBoost, allowlisted skops, edge-aware PyG/NeighborLoader and OOF validation stacking.
Consequence: Hash/schema mismatch fails; no implicit training, model substitution or synthetic data.

## ADR-010: Keep Non-Estimable Primary Results Visible
Status: Accepted; full-network primary evaluation remains open.
Context: Label-independent bounded AMLworld components contain insufficient future positives.
Decision: Publish class counts and null performance; never select cohorts/seeds using test labels.
Consequence: PaySim transaction performance cannot stand in for mule-topology generalization.

## ADR-011: Numerical Calibration Bounds
Status: Accepted after reproducing isotonic output beyond the unit interval.
Context: The installed interpolator emits a small float32 representation overshoot.
Decision: Share a narrow floating-point tolerance correction; record counts and reject larger violations.
Consequence: Valid probabilities without changing ranking, labels, frozen models or operating thresholds.

## ADR-012: Validation Determines the Serving Candidate
Status: Accepted for the candidate serving migration.
Context: Neither simulated split selected the GNN at the specified low-FPR operating point.
Decision: Keep graph-tabular as the selected path; retain GNN/fusion as measured ablations.
Consequence: Do not spend GNN latency or invent missing component values just to market a neural path.

## ADR-013: JDBC Decision Boundary and Durable Transport
Status: Accepted for the platform migration; acceptance remains test-gated.
Context: Legacy JPA controllers and consumers implement competing, non-atomic decision paths.
Decision: Isolate them in legacy; use Flyway plus a tenant-locked JDBC ledger, decisions, audit and outbox.
Consequence: Transport is at-least-once with business-key deduplication, not distributed exactly-once.

## ADR-014: No Automatic Bank Freeze or Feedback Promotion
Status: Accepted for a non-production research platform.
Context: False freezes are harmful and case status is not independently verified fraud evidence.
Decision: Bounded review holds, supervisory actions, appeals and independent cooled adjudication.
Consequence: No bank intervention, recovered-funds claim or automatic case-to-transaction label conversion.

## ADR-015: Generated Client Must Survive a Real Contract Check
Status: Accepted after the first real-stack test exposed empty request serialization.
Context: The old generator mishandles closed OpenAPI objects; its compile success was insufficient.
Decision: Use official OpenAPI normalization, a compatible Spring Boot patch and serialization regression tests.
Consequence: Strict server schemas remain intact; generated files are never manually patched.

## ADR-016: Retire Competing Legacy Execution Paths
Status: Accepted; historical migrations remain for non-destructive upgrades.
Context: Excluding unsafe controllers and pickle training paths by profile still leaves an accidental execution surface.
Decision: Remove retired Java/ML implementations and binary pickle bundles; quarantine legacy database tables from the runtime role.
Consequence: Old endpoints are intentionally unsupported; audit evidence remains anchored to the baseline Git revision.

## ADR-017: Separate Signing Purposes and Restrict Tenant Administration
Status: Accepted for the local research deployment, not a production identity certificate.
Context: A shared HMAC key enables cross-service forgery; an end-user-editable tenant claim defeats isolation.
Decision: Independent ML, stream and ingestion keys; issuer/audience/identity validation; admin-only Keycloak tenant attributes.
Consequence: Real OIDC signature checks and stream isolation tests are required; HTTP identity transport requires an explicit local-only override.

## ADR-018: Audit Official CPU Variants Explicitly
Status: Accepted; version advisory coverage and native binary provenance are separate checks.
Context: PyPI advisory tooling skips CPU-local framework versions, and an older framework constrained a vulnerable build dependency.
Decision: Use compatible official CPU/sampler wheels, pinned hashes, an upstream-release advisory mapping and independent image scans.
Consequence: Unknown skipped packages or unfinished scanners cannot be reported as a clean security result.

## ADR-019: Fail Test Receipts When Source Changes During Execution
Status: Accepted; functional assertions alone do not identify the tested snapshot.
Context: Long-running checks can overlap ongoing edits and otherwise produce misleading final-state acceptance claims.
Decision: Record pre-run source hashes and reject receipts whose post-run source differs; rerun the final snapshot.
Consequence: An intermediate BUILD SUCCESS or passing pytest output is insufficient when the receipt reports changed source.

## ADR-020: Retire Superseded Repository-Root Paths
Status: Accepted following the operator's repository-listing cleanup request.
Context: Duplicate pytest config shadows current settings; old launchers and notebook call retired code, and a deployment file embeds a provider credential.
Decision: Remove superseded root files; centralize configuration/docs; render README values from reports; add hygiene and deployment-secret gates.
Consequence: Old commands are unsupported; provider revocation remains required and historical claims remain only in baseline audit evidence.

## ADR-021: Strict Core Types and Fresh Evaluation Regression
Status: Implemented locally; cross-platform and hosted acceptance remain separately verified.
Context: Dynamic graph/model boundaries and environment-dependent tooling can hide regressions.
Decision: Require strict core typing, explicit lint, branch-aware coverage and fresh seeded training/evaluation against generated golden JSON.
Consequence: Missing dependencies or changed evidence fail; golden regeneration requires explicit review, never an automatic CI fallback.

## ADR-022: Explicit Reproduction Scope and Self-Contained Integration Fixtures
Status: Implemented; local execution evidence is separate from hosted CI acceptance.
Context: Independent scripts and locally prepared models do not establish a clean-checkout reproduction path.
Decision: Require a named dataset and explicit simulator opt-in, verify raw/supplier hashes, preserve immutable candidates and train CI fixtures before integration tests.
Consequence: Full-network AMLworld evaluation fails explicitly until implemented; research command success does not close end-to-end deployment, load or security gates.

## ADR-023: Measure Actual Network Decision Delivery
Status: Implemented with local Testcontainers evidence, not a production SLO.
Context: Model-only and amortized batch timings do not measure Kafka, persistence or investigator delivery.
Decision: Use a real HTTP SSE reader, signed Kafka input and per-transaction monotonic clocks ending after both committed account decisions; bootstrap individual request quantiles.
Consequence: Disclose closed-loop hot-account traffic and excluded ingress/network boundaries; fail degraded runs; never attribute graph-tabular timing to an unselected neural path.

## ADR-024: Bound Telemetry Labels and Preserve Correlation Context
Status: Local stage instrumentation; production collection and full OpenTelemetry tracing remain pending.
Context: Per-account or per-request metric labels leak identifiers and cause unbounded cardinality.
Decision: Use a fixed stage enum, success/error outcomes and framework-generated fixed histogram bounds; emit structured stage logs with scoped correlation IDs, not event bodies or credentials.
Consequence: Verify authenticated metric access and label bounds; restore worker correlation context; histogram instrumentation alone does not establish distributed tracing or a deployed dashboard.

## ADR-025: Bind Drift Monitoring to Training Evidence and Tenant Scope
Status: Implemented locally; production collection and drift-alarm calibration remain separate acceptance work.
Context: An offline drift function or production-derived baseline cannot establish monitored, leakage-audited distribution change.
Decision: Require a hash/schema-verified TRAIN-row reference, bounded tenant/model/reference-specific windows and authenticated tenant-filtered PSI/KS metrics with explicit readiness and expiry.
Consequence: Missing references require retraining; old artifacts remain archived; drift requests data review and controlled shadow retraining, never an automatic freeze, label or promotion.

## ADR-026: Isolate the Approved Public Website from the Fraud Platform
Status: Implemented as a separate static entry; provider deployment receipt records the actual target and retained access protection.
Context: Publishing a landing page must not expose the unfinished investigator UI, internal scoring endpoints or unsupported claims.
Decision: Build only the approved research website, generate displayed evidence from measured reports, label all illustrations, and upload a strict static-file allowlist to a separate Vercel project.
Consequence: No backend or private environment is deployed; customer testimonials and commercial plans are replaced by clearly attributed project principles and research setups; production platform acceptance remains open.

## ADR-027: Replace Substitute Investigator Data with Authenticated Contracts
Status: Checkpoint implementation; browser and deployment acceptance are incomplete.
Context: Retired UI contracts, stored credentials and generated fallback values could misrepresent actual decisions.
Decision: Use verified backend identity/roles, memory-only credentials, scoped header-based SSE and API-only evidence/review/policy/drift views; test against the actual stack.
Consequence: Missing or degraded data remains explicit; the failed mobile browser gate and unverified production OIDC path prevent a completed-platform claim.
