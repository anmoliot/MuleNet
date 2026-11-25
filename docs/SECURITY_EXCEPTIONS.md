# Security Findings and Exceptions

This file is a triage ledger, not a clean-scan certificate. Current counts and
tool outcomes come from reports/*.json. Unknown findings block the gate. Do not
exclude whole source trees or silently ignore a scanner/network failure.

## Historical Credentials

The full-history Gitleaks scan found a public default signing key in an older
environment example, legacy signer and old test configuration. Those exact
historical fingerprints are retained in scripts/triage_secrets.py with status
historical_default_retired_rotate_existing_installations. The legacy signer and
credential initializers are removed, new keys/passwords are independently generated,
and the active JWT decoders do not use the historical key. Git history is not
rewritten. Existing operators must revoke old sessions/users, rotate their old
signing/service/DB/IDP credentials and review access logs; external installations'
rotation has not been verified from this local checkout.

Generated source_sha256 receipt entries also trigger the generic API-key rule.
The triage script accepts these only when their values match actual source blobs
at the scanned commit, including explicitly handled checkout line endings. They
are verified checksums, not a global exception for anything resembling a hash.
See the raw redacted history scan and generated triage report. No unredacted
secret is copied into this ledger or public report.

## Runtime Dependency Remediation

The first locked-runtime audit found JWT and build-tool vulnerabilities. Updating
the JWT pin is straightforward. The old PyTorch release constrained setuptools
below its fixes; the replacement uses an officially available ABI-matched sampler
and a PyTorch release without that cap, not an incompatible dependency override.
The newest framework release lacked the required published sampler wheel at the
time of the check and was not silently used. Fixed pins require the complete
model/export/serving test suite and a fresh audit before acceptance.

pip-audit does not index the CPU-local PyTorch wheel version as a PyPI release.
That skipped row is not a clean result. The gate must additionally audit the
corresponding upstream release and record the distribution mapping; image scans
and official wheel provenance cover different concerns. Missing binary advisory
coverage must remain explicit rather than disappearing from a count.

## Open Boundaries

### Spring Boot 3 Patch Access: Pending Operator Credentials

The current public Spring Framework/Security patch line still triggers advisories.
The operator will configure authorized Spring Enterprise repository access locally;
no credentials are requested in chat or committed. Do not substitute an unlicensed
download or silently migrate to a different major framework. These findings remain
open, and the Java/image aggregate gate remains failed until patched dependencies
are available, installed and retested. The official advisories distinguish OSS
fixes on the newer major line from enterprise fixes on the existing line:
[XsltView](https://spring.io/security/cve-2026-47884/) and
[SSE view fragments](https://spring.io/security/cve-2026-47890/).
The current JSON REST/SSE path does not render XSLT or view fragments; that does
not resolve every other Spring advisory or justify a blanket suppression.

### Container Distribution Advisories: Open, Not Suppressed

The refreshed ML image uses a security-maintenance Python base and updated
Debian packages; the global pip installer was removed. Its latest Trivy report
still lists distribution advisories with no vendor fix. These are not accepted
as a clean scan and are not excluded by severity or an ignore file. Exact package,
version, advisory, vendor status and image identity remain in
[the raw image report](../reports/trivy-ml.json). The aggregate gate stays failed.

The remaining high-severity families include privileged mount/cgroup operations,
ACL traversal, terminal parsing, SQLite extensions, OpenSSL QUIC, systemd-homed,
and archive parsing. The service is non-root, drops Linux capabilities, has a
read-only filesystem and internal authenticated ingress; those constraints reduce
exposure but do not prove each library flaw unreachable. SQLite database uploads,
QUIC listeners, shell commands and arbitrary archive uploads are not scoring API
features. This is contextual triage, not a vulnerability dismissal or exploit
test. Production deployment remains blocked pending vendor remediation or an
organization-approved per-advisory risk review. Project maintainers own that
review; re-scan on each image build and do not carry an exception forward silently.

### Scanner Reliability

The image report repeats the Python base image's public GPG fingerprint, which
Gitleaks flags as a generic API key. The triage script accepts only that exact
public fingerprint in the parsed image environment/history fields, backed by the
[official Python image Dockerfile](https://github.com/docker-library/python/blob/master/3.13/slim-trixie/Dockerfile).
Other fields, paths or values still block publication. This is not a secret-key
exception and does not suppress any vulnerability finding.

The initial backend Trivy attempt exhausted its default deadline during its first
Java database download. A retry uses the completed cache and a longer bounded
timeout. No empty report was substituted. OWASP Dependency-Check's newer release
rejected an absent NVD key despite anonymous NVD requests working; the pinned
compatible scanner is used instead of inventing credentials or claiming a scan
ran. See [the upstream regression](https://github.com/dependency-check/DependencyCheck/issues/8715).

Hosted GitHub Actions have not run merely because workflow files exist. The
single-node Compose Kafka transport is internal, not a production TLS/ACL/HA
configuration. Full data-principal erasure, external audit-head witnessing,
production artifact attestation and operating-organization identity/retention
approval remain deployment responsibilities. Do not enter real bank customer
data or execute real-world adverse actions based on this research installation.
