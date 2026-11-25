import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


def test_bootstrap_is_unique_exclusive_and_never_prints_passwords(tmp_path):
    paths = [tmp_path / "first.env", tmp_path / "second.env"]
    results = []
    for path in paths:
        completed = subprocess.run([sys.executable, str(ROOT / "scripts/bootstrap_secrets.py"), "--demo", "--out", str(path)], capture_output=True, text=True)
        assert completed.returncode == 0
        values = dict(line.split("=", 1) for line in path.read_text().splitlines() if line and not line.startswith("#"))
        assert values["MULENET_ALLOW_SYNTHETIC"] == "true"
        assert values["SPRING_PROFILES_ACTIVE"] == "platform,demo"
        secrets = [value for key, value in values.items() if "PASSWORD" in key or "SECRET" in key or "KEY" in key and key != "KEYCLOAK_ADMIN"]
        assert len(set(secrets)) == len(secrets)
        assert all(value not in completed.stdout for value in secrets)
        results.append(values)
    assert results[0]["MULENET_SERVICE_SECRET"] != results[1]["MULENET_SERVICE_SECRET"]
    before = paths[0].read_bytes()
    completed = subprocess.run([sys.executable, str(ROOT / "scripts/bootstrap_secrets.py"), "--out", str(paths[0])], capture_output=True, text=True)
    assert completed.returncode != 0 and paths[0].read_bytes() == before


def test_audit_detects_tamper_reordering_and_truncation(tmp_path, monkeypatch):
    audit = module("verify_audit")
    entries, previous = [], "GENESIS"
    for seq in range(1, 4):
        payload = json.dumps({"sequence": seq, "action": "UNIT_TEST"})
        head = hashlib.sha256((previous + "\n" + payload).encode()).hexdigest()
        entries.append({"sequence": seq, "previous_hash": previous, "entry_hash": head, "payload": payload})
        previous = head
    assert audit.verify(entries, previous)["anchored"]
    with pytest.raises(ValueError, match="witnessed"):
        audit.verify(entries)
    with pytest.raises(ValueError, match="external witness"):
        audit.verify(entries[:-1], previous)
    with pytest.raises(ValueError, match="sequence"):
        audit.verify(entries[::-1], previous)
    with pytest.raises(ValueError, match="payload hash"):
        audit.verify([dict(entries[0], payload="changed")], allow_unanchored=True)
    input_path, output = tmp_path / "audit.json", tmp_path / "verified.json"
    input_path.write_text(json.dumps(entries), encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["verify_audit", "--file", str(input_path), "--expected-head", previous, "--out", str(output)])
    audit.main()
    assert json.loads(output.read_text())["verified_entries"] == len(entries)
