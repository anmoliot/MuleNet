import pytest
from test_platform_tools import module


def test_golden_comparison_rejects_missing_nonfinite_type_and_metric_drift():
    compare = module("eval_smoke").differences
    expected = {"metric": {"value": 0.5, "ci95": [0.4, 0.6]}, "status": True}
    assert not compare(expected, expected)
    assert not compare(0.5, 0.5000001)
    assert compare(expected, {"status": True})
    assert compare(0.5, float("nan"))
    assert compare(0.5, 0.6)
    assert compare(True, 1)
    assert compare([1], [1, 2])
    assert compare({"m": 0.5}, {"m": 0.6}) == ["root.m: 0.6 != 0.5"]


def test_smoke_requires_explicit_synthetic_opt_in(tmp_path):
    with pytest.raises(ValueError, match="allow-synthetic"):
        module("eval_smoke").run(tmp_path, allow_synthetic=False)


def test_metric_renderer_uses_intervals_and_rejects_missing_evidence():
    render = module("render_readme_metrics")
    model = {"metrics": {"recall": {"value": 0.0, "ci95": [0.0, 0.0]}}, "exact_binomial_ci95": {"recall": [0.0, 0.5]}}
    assert render.estimate(model, "recall")["ci95"] == [0.0, 0.5]
    with pytest.raises(ValueError, match="nonfinite"):
        render.number(float("nan"))
    with pytest.raises(ValueError, match="marker"):
        render.replace_block("no markers", "METRICS", "content")
    original = "before<!-- METRICS:START -->old<!-- METRICS:END -->after"
    assert (
        render.replace_block(original, "METRICS", "new")
        == "before<!-- METRICS:START -->\nnew\n<!-- METRICS:END -->after"
    )


def test_retired_paths_and_unsupported_readme_claims_fail_hygiene(tmp_path):
    hygiene = module("check_repo_hygiene")
    (tmp_path / "README.md").write_text("# Research\n")
    assert not hygiene.inspect(tmp_path)
    (tmp_path / "pytest.ini").write_text("[pytest]\n")
    (tmp_path / "README.md").write_text("enterprise-grade [missing](absent.md)\n")
    assert len(hygiene.inspect(tmp_path)) == 3
