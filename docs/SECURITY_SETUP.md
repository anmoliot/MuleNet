# Security Setup

This checkout is a research system. Passing unit tests does not authorize real
banking decisions or establish production security. Read SECURITY_EXCEPTIONS.md
and the generated security-gate report before deployment.

## Installation Identity

Run `python scripts/bootstrap_secrets.py` on a new installation. It creates
independent credentials exclusively and refuses to overwrite an existing file.
Use `--demo` only for a local simulated demonstration. The normal profile requires
an explicit OIDC issuer and does not enable demo authentication or seeding.

For an older file created by this script, `--upgrade-purpose-keys` appends only
missing ingestion/stream signing keys. It does not rotate existing credentials.
On Windows restrict the generated file's ACL to the installation account. Do not
put production secrets in a synced directory; use a managed secret store.

ML, stream and ingestion signatures use distinct keys and audience/scope checks.
Reusing a key across those purposes fails startup. Rotating encryption keys needs
a versioned re-encryption migration, not just changing an environment variable.
See PRIVACY.md for retention, identifiers, backups and operator responsibilities.

## Optional Local OIDC

The optional `docker-compose.oidc.yml` imports the realm without users or default
passwords. Start just its Keycloak service to configure identity:

```sh
docker compose -f docker-compose.yml -f docker-compose.oidc.yml up -d keycloak
uv run --frozen --group deployment python scripts/configure_keycloak.py
```

The configuration command preserves other managed attributes, restricts tenant
view/edit to identity administrators, disables unmanaged attributes, and reads
the configuration back before writing its verification receipt. Administrators
must assign each investigator's tenant and appropriate realm role through the
identity provider. Self-service tenant editing must remain disabled.

The optional Compose override deliberately enables local HTTP OIDC for loopback
and the internal Keycloak service. Normal configuration requires HTTPS. Keycloak
`start-dev`, its local storage, loopback URLs and this explicit override are not
a production identity deployment. Use an organization-managed HTTPS provider,
approved MFA/session policy and correctly restricted redirect origins there.

## Verification

```sh
uv sync --frozen --all-groups
uv run --frozen --all-groups python scripts/record_tests.py --phase security-python
uv run --frozen --all-groups python scripts/audit_python.py
uv run --frozen --all-groups python scripts/audit_frontend.py
uv run --frozen --all-groups python scripts/check_unsafe_paths.py
uv run --frozen --all-groups python scripts/record_maven_tests.py
uv run --frozen --all-groups python scripts/security_gate.py
```

The Java recorder additionally requires Docker and a locally built ML image plus
the explicit simulated acceptance artifact. Windows can use its `--wsl` switch.
The aggregate gate requires Java dependency, image and secret-history receipts
as well; it is expected to fail if they are missing. It never turns an incomplete
scanner invocation into an empty vulnerability result. Hosted workflow execution
must be verified separately after an authorized push.

Review every scanner finding. Historical public signing defaults are retired,
not secret merely because their files were removed. Existing operators must
revoke old sessions and credentials; this checkout cannot verify remote rotation.
Never blanket-suppress a directory or all unfixed image advisories to obtain a
passing badge. Any accepted risk needs exact scope, rationale, owner and expiry.

## Network Boundary

The base Compose file publishes only loopback application ports. ML, Redis,
Postgres and Kafka have no host port bindings. Internal ML requests require
signed short-lived service credentials; SSE requires its own short-lived bearer
header and tenant/role checks. Query-string credentials are rejected. The local
single-broker Kafka network is not a replacement for production broker TLS/ACLs.

SOFT_HOLD only creates an expiring internal review record. No external funds are
frozen. A model outage records `degraded=true` and a null probability, followed by
human review and an auditable release path. Do not interpret this as successful
fraud detection, recovered money, or a verified positive training label.
