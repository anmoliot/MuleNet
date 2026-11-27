import json
import re
import tomllib
from pathlib import Path

import httpx
from test_platform_tools import module


def test_deployment_secret_rule_detects_literals_not_environment_references():
    root = Path(__file__).resolve().parents[2]
    config = tomllib.loads((root / ".gitleaks.toml").read_text(encoding="utf-8"))
    rule = next(item for item in config["rules"] if item["id"] == "deployment-literal-secret")
    regex = re.compile(rule["regex"])
    fixture = "fixture-only-" + "x" * 24
    assert regex.search(f"  - key: PROVIDER_PASSWORD\n    value: {fixture}\n")
    assert not regex.search("  - key: PROVIDER_PASSWORD\n    value: ${PROVIDER_PASSWORD}\n")
    assert not regex.search("  - key: PROVIDER_PASSWORD\n    value: '${PROVIDER_PASSWORD}'\n")
    assert not regex.search(f"  - key: PUBLIC_LABEL\n    value: {fixture}\n")


def test_deserialization_gate_resolves_aliases_and_requires_weights_only():
    gate = module("check_unsafe_paths")
    assert gate.inspect("import pickle as p\np.load(f)", "test.py")
    assert gate.inspect("from joblib import load as read\nread(f)", "test.py")
    assert gate.inspect("import torch\ntorch.load(f)", "test.py")
    assert not gate.inspect("import torch\ntorch.load(f, weights_only=True)", "test.py")
    assert not gate.inspect("import yaml\nyaml.safe_load(f)", "test.py")


def test_tenant_profile_is_admin_only_and_preserves_existing_attributes():
    setup = module("configure_keycloak")
    current = {"attributes": [{"name": "username"}, {"name": "tenant", "permissions": {"edit": ["user"]}}]}

    def handler(request):
        if request.url.path.endswith("/token"):
            return httpx.Response(200, json={"access_token": "test-only"})
        assert request.headers["Authorization"] == "Bearer test-only"
        if request.method == "PUT":
            current.clear()
            current.update(json.loads(request.content))
            return httpx.Response(204)
        return httpx.Response(200, json=current)

    with httpx.Client(base_url="http://localhost:8081", transport=httpx.MockTransport(handler)) as client:
        assert setup.configure(client, "fixture-admin", "fixture-password")["tenant_edit"] == "admin_only"
    assert next(item for item in current["attributes"] if item["name"] == "username") == {"name": "username"}
    assert next(item for item in current["attributes"] if item["name"] == "tenant")["permissions"] == {
        "view": ["admin"],
        "edit": ["admin"],
    }


def test_security_receipts_fail_closed_for_missing_and_vulnerable_scans(tmp_path):
    gate = module("security_gate")
    assert not gate.assess(tmp_path)["passed"]
    (tmp_path / "trivy-ml.json").write_text(
        json.dumps({"Results": [{"Vulnerabilities": [{"VulnerabilityID": "fixture"}]}]})
    )
    assert gate.assess(tmp_path)["checks"]["trivy-ml.json"] == "failed"
    (tmp_path / "trivy-ml.json").write_text("{}")
    assert gate.assess(tmp_path)["checks"]["trivy-ml.json"] == "missing_or_invalid"


def test_public_gpg_triage_is_limited_to_exact_image_metadata(monkeypatch):
    triage = module("triage_secrets")
    value = f"GPG_KEY={triage.PYTHON_PUBLIC_GPG_FINGERPRINT}"
    content = json.dumps(
        {"Metadata": {"ImageConfig": {"config": {"Env": [value]}, "history": [{"created_by": f"ENV {value}"}]}}},
        indent=2,
    ).encode()
    monkeypatch.setattr(triage, "blob", lambda commit, path: content)
    finding = {"RuleID": "generic-api-key", "File": "reports/trivy-ml.json", "Commit": "a" * 40}
    lines = content.decode().splitlines()
    for index, line in enumerate(lines, 1):
        if value in line:
            assert triage.public_fingerprint_finding(finding | {"StartLine": index})
            assert not triage.public_fingerprint_finding(finding | {"File": ".env", "StartLine": index})
    monkeypatch.setattr(triage, "blob", lambda commit, path: content.replace(value.encode(), b"GPG_KEY=private-value"))
    assert not triage.public_fingerprint_finding(finding | {"StartLine": 1})
