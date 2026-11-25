# As-Of Feature Contract

Scope: the new mulenet_core package, batch materializer and feature-only migration
API. Legacy graph_builder/ml_models/demo paths are NOT migrated and must not be
served as though they use this schema. They remain quarantined audit findings
until artifact verification and full train/serve replacement in Phase 2.

## Time and Labels

Transactions have strict nonnegative integer UTC epoch seconds, finite
nonnegative amounts and stable IDs. Unknown fraud labels are None, never silently
negative. Offline/online share extract_features; online arrival order and repeated
identical events do not change a snapshot. Conflicting duplicate IDs fail.
Features ignore future edges and all fraud/typology/ring annotations. Account
creation comes from explicit registry metadata or first observed activity, with
an account_age_known indicator. A transaction before registered creation fails.

All window boundaries are (t - window, t]. Labels are whether the focal account
receives OR sends a flagged edge in (t, t + horizon]. A completeness watermark
must cover the entire label window. An unknown label within that window fails;
an empty complete window is negative. Event time is assumed observable at arrival;
this is not a bitemporal label/late-arrival production history system. The latter
must distinguish event time, observed time and adjudication time before deployment.

## Formulas

- Degree counts transactions; unique-counterparty features separately count IDs.
  Multigraphs preserve repeated payments. Money sums are log1p-transformed.
- Counterparty entropy aggregates incoming amounts by sender, applies Shannon
  log2 entropy, and divides by log2(incoming transaction count). Zero/one incoming
  edge has zero entropy. It is not normalized by the full dataset.
- Pass-through is min(sent, received)/max(received, epsilon). A receiver-only sink
  or outgoing-only source is zero. Fan-out/fan-in use unique-counterparty ratios.
- Dwell is median matched receipt-to-onward delay using FIFO matching of amounts;
  partial matches each contribute one duration. It is not balance-weighted median.
  No match is zero with dwell_observed false. Tied times order by transaction ID.
- Velocity z-score compares the window activity count with disjoint equal-length
  historic buckets, including empty buckets, and floors standard deviation at one.
  New-payee ratio counts outgoing transactions whose payee was unseen before the
  current window; it does not use future counterparties.
- Burstiness is (std - mean)/(std + mean) over activity interarrival intervals,
  with insufficient/degenerate history mapped to zero.
- Round-amount share counts outgoing amounts divisible by the configured fixed
  currency-unit granularity used in code; structuring share is outgoing amounts in
  [0.95 * configured threshold, threshold). These are features, not legal rules.
- Device/IP sharing counts other originators with an observed matching identifier
  in the window. Device metadata belongs to the originating event, not both
  endpoints. Missingness is explicit; absence is not evidence of a clean device.
- Hop flow is log1p amount across edges whose source has minimum directed distance
  hop-1 from the focal account (reverse graph for incoming). Each edge is counted
  once per hop depth; this is not conserved money tracing or an economic recovery.
- Cycle membership uses directed simple cycles bounded in length; clustering uses
  the undirected amount-collapsed window graph; PageRank uses amount weights with
  fixed convergence controls. Node/edge/cycle budgets fail loudly, never truncate
  silently or substitute centrality zeros on numerical/dependency failure.
- Balance-delta error is log1p median absolute payment/balance residual on already
  observed events, with availability flag. Future/current-label-window balances
  cannot enter the features. This is not a claim of predictive usefulness in PaySim.

Exact default windows/bounds and field ordering are code/configuration in
schema.py; feature_schema_hash includes their names, schema, definition version
and config. Any semantic change requires a definition-version bump. Generated
foundation receipts separately hash the implementation source and environment.

## Splits and Limits

Temporal splits purge rows whose future-label horizon reaches the next partition;
train labels finish before validation begins and validation labels finish before
test begins. Validation/test label-window edge IDs cannot appear in train feature
dependencies. Entity splits first partition whole weak components and ring IDs,
then materialize from isolated partition edges. Shared ring IDs join components.
A giant component preventing independent partitions raises rather than randomly
splitting its accounts. Device-sharing features are recomputed within the partition;
this is an inductive isolated-context protocol, not access to heldout identities.

This reference implementation prioritizes correct deterministic semantics over
large-graph throughput: it retains input events and recomputes graph statistics.
It is not the requested Redis bounded-adjacency production implementation and
has no latency guarantee. Downloaded benchmark adapters preserve chronology and
labels; they do not silently sample edges to fit the reference graph budget.

## Feature-Only Migration API

feature_service:create_app is an isolated FastAPI factory. Startup requires an
operator-provided MULENET_FEATURE_SERVICE_TOKEN; there is no credential default.
POST /features checks the bearer secret with constant-time comparison and rejects
strict schema violations. It returns only the feature vector and schema hash,
not scores, freeze actions or synthetic performance. Bind to loopback for local
testing. This narrow bearer gate is NOT a claim of completed Phase 5 mTLS/OIDC,
rate limiting, tenancy, body-byte limits, audit/PII hardening or production readiness.
