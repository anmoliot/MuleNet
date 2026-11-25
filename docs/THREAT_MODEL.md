# Threat Model

## Trust Boundaries

Browser/OIDC -> authenticated backend -> signed Kafka inputs -> tenant-locked DB
decision transaction -> signed internal ML API/Redis -> policy/outbox -> scoped
SSE. The identity provider, deployment operator, secret store and trusted artifact
root are privileged boundaries. A model-file digest is not an artifact signature.
The shipped Compose topology is a loopback-only research deployment, not an HA
bank deployment or an internet-facing production hardening certificate.

| STRIDE / Threat | Mitigation | Verification and Residual Risk |
| --- | --- | --- |
| Spoofing: forged ingestion | OIDC tenant/roles, originator/transaction tokenization, separate-purpose signed Kafka envelopes; no legacy public intake | Real-stack forged-token DLQ assertion; SecurityBoundaryTest verifies signatures/issuer/audience. Broker ACLs/TLS remain required for multi-host production. |
| Tampering: replay or changed duplicate | Stable business key, canonical payload hash, atomic ledger/decision/outbox, account partition key | Integration replay and conflicting duplicate assertions. Transport remains at-least-once; global event-time ordering is not claimed. |
| Tampering: watchlist injection | No external agency connectivity; typed simulated provider has no probability uplift or update endpoint | Simulated adapter checks and strict API schemas. Any future external feed needs independent authentication, provenance and appeal review. |
| Tampering: feedback poisoning | Independent cooled consensus, supervisory adjudication, reviewer-concentration limits; no case-status-to-fraud conversion | test_feedback.py. Evidence linkage, representative negatives and candidate evaluation remain required; automatic feedback promotion is absent. |
| Information disclosure: scoring/model extraction | Internal-only ML network, short-lived scoped service JWT, tokenized inputs, request bounds, authenticated/limited ingestion | Serving negative tests and request-boundary tests. Authorized repeated queries can still reveal model behavior; audit and monitor usage. |
| Information disclosure: SSE | Separately keyed scoped short-lived bearer, tenant query predicates, known-role checks, expiry/connection caps; no query credentials | Signature/scope tests plus actual connected-stream replay and cross-tenant non-disclosure assertions. Proxy logs must not retain query secrets; application clients never put tokens in URLs. |
| Information disclosure: PII/logs | HMAC identifiers, AES-GCM originals/rationales, no original identifiers in ML context, encrypted bounded DLQ with hashed keys | Crypto/stack tokenization tests. Pseudonymization still permits linkage; storage/backups and operator access need separate controls. |
| Elevation: insider override | Supervisor/admin method security, rationale, optimistic version check, bounded holds/expiry, encrypted notes, append-only audit | Stack analyst-denial/release/expiry/audit assertions. No external bank freeze exists; privileged hosts/DB owners require external oversight. |
| Repudiation: audit rewriting/truncation | DB immutability/least privilege, predecessor hashes and verification CLI with external head | Crypto/DB tests and verify_audit tests. Unanchored chains cannot prove completeness or defeat a privileged owner rewriting everything. |
| Tampering: substituted model | Required native formats, schema and per-file hashes before parser invocation, allowlisted skops types, read-only model mount | Artifact mutation/schema/unapproved-type tests. A malicious trusted deployer can replace a manifest too; signed release provenance is an operational boundary. |
| Evasion: delayed/split/merchant relay | As-of features and measured attack suite; graph/tabular candidates compared on validation | Generated adversarial reports. Low baseline recall can make a zero recall drop uninformative; no adversarial-robustness claim. |
| DoS: resource exhaustion | Body/header/scalar/depth bounds, bounded graph/cycle/ego context, rate/connection limits, hard GNN process deadline, circuit breaker | Boundary and actual process-termination tests. Limits are per instance; large-network scalability and distributed rate budgets remain unproven. |
| DoS: poison/dependency failure | Commit only durable effects; retry then bounded encrypted DLQ; cache miss requires authoritative backfill; ML failure creates explicit review state | Real Kafka/DB/Redis/ML test. DLQ publication failure intentionally prevents acknowledgement; operators need backlog/replay monitoring. |
| Supply chain | Locked dependencies, official CPU wheels, secret/history audit, vulnerability/image/SBOM gates | Scanner reports and SECURITY_EXCEPTIONS.md. A configured workflow is not evidence that a scan ran or passed. |

## Harm and Degradation

SOFT_HOLD is an internal, expiring review record, not blocked funds. A failed model
call has null probability and degraded=true. It must not become a low-risk score,
an automatic hard freeze, confirmed fraud, or a positive training label. Analysts
need a review/release path. Policy monetary costs are assumptions. No recovered
money, agency-confirmed watchlist match or compliant STR filing is established.
