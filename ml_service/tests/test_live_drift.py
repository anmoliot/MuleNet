import json
from types import SimpleNamespace

import pytest
from live_drift import LiveDrift
from mulenet_core.drift_reference import DriftReference, load_reference
from mulenet_core.schema import FeatureConfig, feature_names, feature_schema_hash
from prometheus_client import CollectorRegistry, generate_latest
from pydantic import ValidationError


def candidate(version="fixture"):
    names = feature_names()
    data = {
        "feature_schema_hash": feature_schema_hash(),
        "feature_names": list(names),
        "source_split": "TRAIN",
        "data_provenance": "synthetic",
        "selection": "seeded uniform sample without replacement",
        "seed": 42,
        "train_rows": 100,
        "features": [[float(i)] * len(names) for i in range(100)],
        "scores": {name: [i / 100 for i in range(100)] for name in ("tabular_graph", "gnn", "fusion")},
    }
    reference = DriftReference.model_validate_json(json.dumps(data))
    return SimpleNamespace(
        drift_reference=reference, manifest={"model_version": version, "files": {"drift-reference.json": "a" * 64}}
    )


def observe(monitor, bundle, tenant, value):
    monitor.observe(
        tenant, bundle, dict.fromkeys(feature_names(), float(value)), min(float(value) / 100, 1.0), "tabular_graph"
    )


def test_insufficient_samples_are_not_reported_as_zero_drift_and_tenants_are_isolated():
    monitor = LiveDrift(CollectorRegistry(), minimum=4, window=8)
    bundle = candidate()
    observe(monitor, bundle, "bank-a", 50)
    first = monitor.snapshot("bank-a")[0]
    assert not first["ready"] and first["statistics"] is None
    assert b"mulenet_ml_drift_psi{" not in monitor.metrics("bank-a")
    assert monitor.snapshot("bank-b") == []
    assert b"fixture" not in monitor.metrics("bank-b")
    for _ in range(8):
        observe(monitor, bundle, "bank-a", 500)
    shifted = monitor.snapshot("bank-a")[0]
    assert shifted["samples"] == 8 and shifted["ready"] and shifted["review_required"]
    assert shifted["statistics"][feature_names()[0]]["psi"] > 0
    metrics = monitor.metrics("bank-a")
    assert b"mulenet_ml_drift_psi{" in metrics
    assert b"bank-a" not in metrics and b"tenant=" not in metrics and b"account=" not in metrics


def test_window_capacity_expiry_and_reference_identity_are_explicit():
    now = [0.0]
    registry = CollectorRegistry()
    monitor = LiveDrift(registry, minimum=2, window=2, capacity=2, max_age_seconds=10, clock=lambda: now[0])
    bundle = candidate()
    observe(monitor, bundle, "a", 1)
    observe(monitor, bundle, "a", 2)
    changed = candidate()
    changed.manifest["files"]["drift-reference.json"] = "b" * 64
    observe(monitor, changed, "a", 3)
    assert len(monitor.snapshot("a")) == 2
    assert sum(line.startswith(b"mulenet_ml_drift_samples{") for line in monitor.metrics("a").splitlines()) == 2
    observe(monitor, bundle, "b", 4)
    assert len(monitor.windows) == 2
    assert b"mulenet_ml_drift_window_evictions_total 1.0" in generate_latest(registry)
    assert len(monitor.snapshot("a")) == 1
    now[0] = 11.0
    expired = monitor.snapshot("a")[0]
    assert expired["samples"] == 0 and not expired["ready"] and expired["statistics"] is None


def test_reference_requires_train_only_aligned_finite_data_and_running_schema(tmp_path):
    reference = candidate().drift_reference
    path = tmp_path / "drift-reference.json"
    path.write_text(reference.model_dump_json())
    assert load_reference(tmp_path, FeatureConfig()) == reference
    for change in ({"source_split": "TEST"}, {"features": [[float("nan")]]}, {"scores": {}}, {"train_rows": 2}):
        with pytest.raises(ValidationError):
            DriftReference.model_validate_json(json.dumps(reference.model_dump(mode="json") | change))
    with pytest.raises(ValueError, match="schema"):
        load_reference(tmp_path, FeatureConfig(currency="USD"))
    path.unlink()
    with pytest.raises(FileNotFoundError):
        load_reference(tmp_path, FeatureConfig())


def test_bad_observations_fail_without_disabling_monitoring():
    monitor = LiveDrift(CollectorRegistry())
    bundle = candidate()
    with pytest.raises(ValueError, match="reference"):
        monitor.observe("a", bundle, {}, 0.5, "tabular_graph")
    for value in (float("nan"), 1.1):
        with pytest.raises(ValueError, match="probability"):
            monitor.observe("a", bundle, dict.fromkeys(feature_names(), 0.0), value, "tabular_graph")
    assert monitor.snapshot("a") == []
    with pytest.raises(ValueError, match="configuration"):
        LiveDrift(CollectorRegistry(), minimum=10, window=2)
