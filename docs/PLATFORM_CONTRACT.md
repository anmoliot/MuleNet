# Candidate Platform Contract

This migration is a research decisioning path, not a connection to a bank's
freeze infrastructure. Every hold is an internal review record. No current
candidate is approved for production decisions. See generated evaluation reports
for poor low-FPR account-forecast performance and non-estimable primary cohorts.

## Ingestion and Durability

The new default Spring profile is platform. The legacy profile is a quarantined
test/migration surface and must not be deployed. The demo profile additionally
enables per-install local demo login and the admin-only seed endpoint. Normal
platform deployments require an OIDC issuer, audience, tenant claim and the
analyst, supervisor, admin or auditor role; there is no default identity.

Authenticated ingestion tokenizes identifiers with tenant/domain-separated HMAC
and encrypts the original payload using AES-GCM. A DB outbox records signed Kafka
inputs. Partition keys are tenant plus source account token. A successful HTTP
acceptance means durably queued, not necessarily scored. Duplicate identifiers
with different bodies are rejected. Kafka consumers commit only after the DB
transaction or successful DLQ publication; transient retries are bounded.

The ledger, decision, policy version, audit entry and decision outbox commit
together. A crash after Kafka publication but before marking an outbox row may
republish it; business-key deduplication prevents duplicate decisions. This is
at-least-once transport with transactional DB effects, not a distributed
exactly-once claim. Arbitrary producer input cannot bypass the signed envelope.
Dead letters contain encrypted bodies and hashes, not cleartext identifiers.
Admin replay re-signs only previously accepted tenant-bound input and is audited.

The reference implementation deliberately rejects late events behind the tenant
watermark. Reordering across account partitions can therefore produce DLQ entries;
global event-time reordering/backfill remains a deployment limitation. Historical
replay must not silently rewrite previously recorded decisions.

## Features and Degradation

Authoritative, complete bounded ledger snapshots backfill an immutable,
content-addressed Redis cache. Cache expiry/eviction is a miss, not permission to
compute partial features. The same feature code computes training and serving
vectors. Large contexts fail explicitly instead of sampling or truncating the
graph. This reference snapshot cache does not establish large-network scalability.
Model context is complete; only displayed evidence is capped and marked when
truncated. Account creation is not inferred as verified registration history.

The serving artifact must pass hash/schema verification. The validation-selected
graph-tabular path is the current default. Neural candidates use bounded ego
graphs and an isolated process: a hard deadline terminates computation and opens
a circuit before an explicit graph-tabular fallback. Missing GNN scores are null,
never invented inputs to fusion. A failed ML/feature/cache/contract call yields
rules-only plus a bounded SOFT_HOLD and degraded=true with no fabricated model
probability. Alerts include model/schema/policy versions and stored explanations.

## Policy and Review

Versioned policy writes require admin authorization, a rationale and optimistic
concurrency. Monetary costs are configurable assumptions, not measured losses.
The review threshold respects that cost bound and the saved validation operating
point unless explicitly overridden. Holds expire automatically. Analyst notes
and appeals are supported; supervisor/admin approval and release are audited.
Approval does not execute an external freeze or extend expiry.

Adjudications are not inferred from case status. The feedback quality gate
requires independent cooled agreement and supervisory review; disputed or
concentrated feedback is quarantined. Account adjudications cannot automatically
become transaction labels. Verified event linkage, representative negatives,
protected evaluation cohorts and shadow comparison remain mandatory before
training/promotion; automatic end-to-end feedback retraining is not implemented.

## Streams and Models

SSE uses a separately scoped short-lived stream token, sent in an Authorization
header, not a query string. Tenant/role checks apply before connection and to
durable replay. Streams expire, have connection limits and support Last-Event-ID.
No synthetic live events are created by the stream handler.

The lightweight registry verifies measured candidate bundles, supports stable
account-hashed canaries and non-policy shadow scores, and atomically changes its
read-only serving pointer. The current rollout adapter supports graph-tabular
candidates only; neural multi-version rollout is explicitly rejected. Rollback:

```text
python -m model_registry rollback --root ../artifacts --allow-synthetic
```

The flag is only appropriate for explicit simulations. Model hashes are
integrity checks, not signatures; trusted read-only artifact deployment and
external audit-head anchoring remain operational requirements.

WatchlistProvider ships only SimulatedI4CProvider. There is no I4C/NCRP credential,
government feed, probability uplift or confirmed agency match. STR exports are
JSON draft/templates, not submitted or certified regulatory filings.
