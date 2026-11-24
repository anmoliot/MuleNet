import json
from pathlib import Path
import time
import uuid

from fastapi.testclient import TestClient
import jwt
import numpy as np
import pytest
import torch

from adjacency_cache import SnapshotCache, snapshot_digest
from gnn_deadline import GnnDeadline
from mulenet_core.models import ModelBundle
from mulenet_core.schema import Account, FeatureConfig, Transaction
from serving import create_app
from simulation.generator import SimulationConfig, generate
from training.experiment import train_experiment

SECRET = "test-only-" + "s" * 64


class MemoryRedis:
    def __init__(self):
        self.data = {}

    def set(self, key, value, ex, nx):
        assert ex > 0 and nx
        self.data.setdefault(key, value)

    def get(self, key):
        return self.data.get(key)


def token(tenant="bank-a", scope="score cache contract metrics", **overrides):
    claims = {"iss": "mulenet-backend", "aud": "mulenet-ml", "sub": "backend", "tenant": tenant,
              "scope": scope, "jti": str(uuid.uuid4()), "iat": int(time.time()), "exp": int(time.time()) + 30}
    claims.update(overrides)
    return {"Authorization": "Bearer " + jwt.encode(claims, SECRET, algorithm="HS256")}


@pytest.fixture(scope="module")
def bundle(tmp_path_factory):
    directory = tmp_path_factory.mktemp("serving") / "candidate"
    data = generate(SimulationConfig(components=6, accounts_per_component=10, days=18, noise_events_per_day=2))
    train_experiment(data, "sim", "temporal", directory, FeatureConfig(), epochs=2)
    return ModelBundle(directory, allow_synthetic=True)


def context():
    events = [Transaction(transaction_id="t1", source="a", target="b", ts=100, amount=100.)]
    accounts = [Account(account_id="a", created_at=0), Account(account_id="b", created_at=0)]
    snapshot_id = snapshot_digest(0, 200, events, accounts)
    return {"snapshot_id": snapshot_id, "complete_from": 0, "watermark": 200,
            "events": [e.model_dump() for e in events], "accounts": [a.model_dump() for a in accounts]}


def test_internal_auth_scope_tenant_and_cache_hash(bundle):
    client = TestClient(create_app(bundle=bundle, cache=SnapshotCache(MemoryRedis()), secret=SECRET))
    snapshot = context()
    request = {"account_id": "b", "as_of": 200, "snapshot_id": snapshot["snapshot_id"], "correlation_id": "test-id"}
    assert client.post("/v1/score", json=request).status_code == 401
    assert client.post("/v1/score", json=request, headers=token(scope="cache")).status_code == 403
    for overrides in ({"aud": "browser"}, {"iss": "other"}, {"exp": int(time.time()) - 10}, {"exp": int(time.time()) + 600}, {"sub": "analyst"}):
        assert client.post("/v1/score", json=request, headers=token(**overrides)).status_code == 401
    assert client.post("/v1/snapshots", json=snapshot, headers=token()).status_code == 200
    assert client.post("/v1/score", json=request, headers=token(tenant="bank-b")).status_code == 409
    response = client.post("/v1/score", json=request, headers=token())
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["model_version"] == bundle.manifest["model_version"]
    assert result["data_provenance"] == "synthetic"
    assert result["score_components"]["gnn"] is None
    assert result["reason_codes"][0]["features"]
    assert result["evidence"]["edges"][0]["transaction_id"] == "t1"
    assert result["simulated_watchlist"]["simulated"]
    assert client.get("/metrics").status_code == 401
    assert client.get("/metrics", headers=token(scope="metrics")).status_code == 200
    bad = dict(snapshot, snapshot_id="0" * 64)
    assert client.post("/v1/snapshots", json=bad, headers=token()).status_code == 422
    snapshot["events"][0]["fraud"] = True
    assert client.post("/v1/snapshots", json=snapshot, headers=token()).status_code == 422
    request["as_of"] = 201
    assert client.post("/v1/score", json=request, headers=token()).status_code == 422
    assert client.post("/v1/score", content=b" " * 2_000_001, headers=token()).status_code == 413
    contract = client.get("/openapi.json", headers=token(scope="contract")).json()
    assert "ScoreResponse" in contract["components"]["schemas"]


def test_gnn_failure_is_explicit_graph_fallback_not_fake_component(bundle):
    class FailedGnn:
        def predict(self, graph):
            raise TimeoutError("injected deadline")

        def close(self):
            pass

    old = bundle.training.get("selected_model")
    bundle.training["selected_model"] = "gnn"
    try:
        client = TestClient(create_app(bundle=bundle, cache=SnapshotCache(MemoryRedis()), secret=SECRET, gnn=FailedGnn()))
        snapshot = context()
        client.post("/v1/snapshots", json=snapshot, headers=token()).raise_for_status()
        response = client.post("/v1/score", json={"account_id": "b", "as_of": 200, "snapshot_id": snapshot["snapshot_id"], "correlation_id": "failure-test"}, headers=token())
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["degraded"] and result["model"] == "tabular_graph"
        assert result["degradation_reason"] == "injected deadline"
        assert result["score_components"]["gnn"] is None
    finally:
        if old is None:
            bundle.training.pop("selected_model", None)
        else:
            bundle.training["selected_model"] = old


def test_gnn_hard_timeout_terminates_worker(bundle):
    from torch_geometric.data import Data
    runner = GnnDeadline(bundle.directory / "gnn.ts", timeout_seconds=.000001, cooldown_seconds=1)
    try:
        assert runner.ready.wait(timeout=30), "Actual GNN worker failed to load"
        graph = Data(x=torch.zeros(1000, len(bundle.names)), edge_index=torch.empty(2, 0, dtype=torch.long), edge_attr=torch.empty(0, 3))
        process = runner.process
        with pytest.raises(TimeoutError, match="hard deadline"):
            runner.predict(graph)
        assert not process.is_alive()
        with pytest.raises(TimeoutError, match="circuit open"):
            runner.predict(graph)
    finally:
        runner.close()


def test_missing_configuration_never_starts_demo(monkeypatch):
    monkeypatch.delenv("MULENET_SERVICE_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="SERVICE_SECRET"):
        create_app()
    monkeypatch.delenv("MULENET_MODEL_DIR", raising=False)
    with pytest.raises(RuntimeError, match="MODEL_DIR"):
        create_app(secret=SECRET)


def test_actual_evaluated_registry_shadow_canary_and_rollback(bundle, tmp_path):
    import shutil
    from eval.run_eval import evaluate
    from model_registry import ModelRegistry, update
    from mulenet_core.io import canonical_json
    data = generate(SimulationConfig(components=6, accounts_per_component=10, days=18, noise_events_per_day=2))
    data_path = tmp_path / "fixture.json"
    data_path.write_bytes(canonical_json(data.model_dump(mode="json")))
    root = tmp_path / "registry"
    root.mkdir()
    shutil.copytree(bundle.directory, root / "first")
    evaluate("sim", data_path, "temporal", root / "first", tmp_path / "metrics.json", True, attacks=False)
    # Duplicate measured test fixture, not a second claimed model result.
    shutil.copytree(root / "first", root / "second")
    update(root, "init", "first", allow_synthetic=True)
    registry = ModelRegistry(root, allow_synthetic=True)
    assert registry.choose("tenant", "a").directory.name == "first"
    update(root, "canary", "second", percentage=100, allow_synthetic=True)
    assert registry.choose("tenant", "a").directory.name == "second"
    update(root, "shadow", "first", allow_synthetic=True)
    from mulenet_core.features import extract_features
    features = extract_features(data.transactions, data.accounts[0].account_id, max(e.ts for e in data.transactions))
    assert registry.shadow(features)[0]["used_for_policy"] is False
    update(root, "promote", "second", allow_synthetic=True)
    assert registry.active.directory.name == "second"
    update(root, "rollback", allow_synthetic=True)
    assert registry.active.directory.name == "first"
    with pytest.raises(ValueError, match="Invalid registry version"):
        update(root, "promote", "../escape", allow_synthetic=True)
    with pytest.raises(ValueError, match="percentage"):
        update(root, "canary", "second", percentage=101, allow_synthetic=True)
