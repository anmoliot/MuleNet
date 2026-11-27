import json

import pytest
from test_platform_tools import module


def test_simulator_reproduction_requires_opt_in_preserves_input_and_is_deterministic(tmp_path, monkeypatch):
    reproduce = module("reproduce")
    monkeypatch.setattr(reproduce, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="allow-synthetic"):
        reproduce.simulator_data(allow_synthetic=False)
    path, first = reproduce.simulator_data(allow_synthetic=True)
    _, second = reproduce.simulator_data(allow_synthetic=True)
    assert first == second
    ledger = json.loads(path.with_suffix(".cashouts.json").read_bytes())
    assert ledger["data_hash"] == first["sha256"]
    path.write_text("changed")
    with pytest.raises(FileExistsError):
        reproduce.simulator_data(allow_synthetic=True)
    assert path.read_text() == "changed"


def test_reproduction_rejects_unsafe_run_ids_and_incomplete_primary_benchmark(tmp_path, monkeypatch):
    reproduce = module("reproduce")
    monkeypatch.setattr(reproduce, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="identifier"):
        reproduce.execute("data", "sim", run_id="../escape", allow_synthetic=True)
    with pytest.raises(ValueError, match="Unknown"):
        reproduce.execute("other", "sim")
    monkeypatch.setattr(reproduce, "benchmark_input", lambda *args: (tmp_path / "input.csv", {"sha256": "fixture"}))
    with pytest.raises(RuntimeError, match="NOT a replacement"):
        reproduce.execute("train", "amlworld")
    assert not (tmp_path / "reports/runs/repro-v1/train-amlworld.json").exists()


def test_benchmark_reproduction_verifies_data_and_supplier_metadata(tmp_path, monkeypatch):
    reproduce = module("reproduce")
    monkeypatch.setattr(reproduce, "ROOT", tmp_path)
    path = tmp_path / "data/raw/paysim" / reproduce.DATASETS["paysim"][1]["default"]
    path.parent.mkdir(parents=True)
    path.write_text("fixture")
    metadata = path.parent / "default-supplier-metadata.json"
    metadata.write_text("{}")
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "data-paysim-default.json").write_text(
        json.dumps({"sha256": reproduce.sha256(path), "supplier_metadata_sha256": reproduce.sha256(metadata)})
    )
    assert reproduce.benchmark_input("paysim", "default")[0] == path
    metadata.write_text("changed")
    with pytest.raises(ValueError, match="metadata"):
        reproduce.benchmark_input("paysim", "default")
    path.write_text("changed")
    with pytest.raises(ValueError, match="hash mismatch"):
        reproduce.benchmark_input("paysim", "default")
