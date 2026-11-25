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
Status: Blocked pending user-supplied authorized datasets/authentication.
Context: CSVs/credentials are absent; user said they will provide inputs later.
Decision: Finish isolated foundation checks; do not replace primary benchmark evaluation with demo claims.
Consequence: Model/benchmark phases and overall acceptance remain incomplete.

## ADR-007: Balance and Clock Semantics
Status: Accepted for reference feature extraction.
Context: PaySim balances may describe outcomes; AMLworld clocks have no explicit timezone.
Decision: Use past-event balances only; treat simulation timestamps as a documented UTC clock convention.
Consequence: No current-transaction balance leakage or claim of real-world temporal availability.
