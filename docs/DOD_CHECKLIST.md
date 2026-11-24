# Definition of Done: Not Complete

Do not treat feature-foundation unit tests as production readiness. The work is
blocked on authorized benchmark inputs for training/evaluation; the user will
provide these later. Main is unchanged and its CI health is not established.

- [ ] Clean-checkout setup/data/train/eval/bench/test/lint: no full pipeline yet.
- [ ] Safe model loading and manifest/schema verification: legacy pickle loaders remain.
- [ ] Complete leakage-audited benchmark results: core feature/split tests exist; no temporal/entity benchmark evaluations yet.
- [ ] Real message-passing GNN, low-FPR ablation and latency evidence: not implemented/evaluated.
- [ ] Generated README metrics and load percentiles: README still contains quarantined legacy claims, see AUDIT.md.
- [ ] Degradation, idempotency, DLQ and audit chain: no stack integration evidence.
- [ ] Authentication/secrets/supply-chain gates: legacy exposures remain; not production safe.
- [ ] Required threat/model/runbook/privacy documentation: incomplete.

Available evidence: [audit](AUDIT.md), [architecture](ARCHITECTURE.md),
[execution log](CHANGELOG_AGENT.md), [decisions](DECISIONS.md),
[generated foundation receipt](../reports/phase1-foundation.json).
