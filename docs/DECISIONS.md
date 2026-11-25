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
