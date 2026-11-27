import json
from types import SimpleNamespace

import pytest
from test_platform_tools import module


def load():
    return {
        "durations_ms": [float(i + 1) for i in range(100)],
        "requests": 100,
        "elapsed_seconds": 2.0,
        "concurrency": 1,
        "degraded_decisions": 0,
    }


def test_pipeline_quantiles_use_individual_timings_with_reproducible_intervals():
    benchmark = module("bench_pipeline")
    first = benchmark.summarize_load(load())
    assert first == benchmark.summarize_load(load())
    assert first["quantiles"]["p50_ms"]["value"] == 50.5
    assert first["quantiles"]["p99_ms"]["value"] == pytest.approx(99.01)
    assert first["completed_per_second"] == 50
    for value in first["quantiles"].values():
        assert value["ci95"][0] <= value["value"] <= value["ci95"][1]


def test_pipeline_rejects_degraded_missing_nonfinite_or_small_samples():
    benchmark = module("bench_pipeline")
    for bad in (
        load() | {"degraded_decisions": 1},
        load() | {"durations_ms": [1.0]},
        load() | {"durations_ms": [float("nan")] * 100},
        load() | {"elapsed_seconds": 0},
    ):
        with pytest.raises(ValueError):
            benchmark.summarize_load(bad)


def test_pipeline_requires_opt_in_and_does_not_reuse_old_measurements(tmp_path, monkeypatch):
    benchmark = module("bench_pipeline")
    monkeypatch.setattr(benchmark, "ROOT", tmp_path)
    output = tmp_path / "reports/latency.json"
    with pytest.raises(ValueError, match="allow-synthetic"):
        benchmark.run_pipeline(allow_synthetic=False, wsl=False, output=output)
    raw = tmp_path / ".tools/pipeline-latency-raw.json"
    raw.parent.mkdir()
    raw.write_text('{"stale":true}')
    monkeypatch.setattr(benchmark.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1))
    with pytest.raises(RuntimeError, match="benchmark failed"):
        benchmark.run_pipeline(allow_synthetic=True, wsl=False, output=output)
    assert not raw.exists()
    assert json.loads(output.read_bytes())["metrics"] is None
