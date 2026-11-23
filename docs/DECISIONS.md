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
