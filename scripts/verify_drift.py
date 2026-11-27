"""Probe actual drift-monitor behavior; constructed shifts are not fraud metrics."""

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from prometheus_client import CollectorRegistry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_service"))

from live_drift import LiveDrift
from mulenet_core.artifacts import sha256
from mulenet_core.models import ModelBundle


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args()
    if not args.allow_synthetic:
        parser.error("Constructed drift validation requires explicit --allow-synthetic")
    source_files = [path for path in args.models.iterdir() if path.is_file()]
    pointer = args.models.parent / "registry.json"
    if pointer.exists():
        source_files.append(pointer)
    before = {path: sha256(path) for path in source_files}
    bundle = ModelBundle(args.models, allow_synthetic=True)
    reference = bundle.drift_reference
    rows = np.asarray(reference.features)
    probabilities = reference.scores["tabular_graph"]
    monitor = LiveDrift(CollectorRegistry(), window=len(rows), minimum=len(rows))
    for features, score in zip(rows, probabilities, strict=True):
        monitor.observe(
            "reference-probe", bundle, dict(zip(bundle.names, features, strict=True)), score, "tabular_graph"
        )
    baseline = monitor.snapshot("reference-probe")[0]
    channel = bundle.names.index("log_sent_86400s")
    shifted = rows.copy()
    shifted[:, channel] += max(1.0, float(np.std(rows[:, channel])) * 5)
    for features, score in zip(shifted, probabilities, strict=True):
        monitor.observe("shift-probe", bundle, dict(zip(bundle.names, features, strict=True)), score, "tabular_graph")
    measured = monitor.snapshot("shift-probe")[0]
    isolated = monitor.snapshot("unobserved-tenant") == []
    unchanged = before == {path: sha256(path) for path in source_files}
    passed = not baseline["review_required"] and measured["review_required"] and isolated and unchanged
    report = {
        "passed": passed,
        "data_provenance": "synthetic",
        "probe": "Constructed train-reference replay and feature shift, NOT live fraud effectiveness",
        "model_version": bundle.manifest["model_version"],
        "reference_sha256": bundle.manifest["files"]["drift-reference.json"],
        "source_split": reference.source_split,
        "baseline": baseline,
        "shifted": measured,
        "tenant_isolation_verified": isolated,
        "artifact_and_existing_registry_files_unchanged": unchanged,
        "limitations": [
            "Offline behavioral probe, not a calibrated false-drift-alarm rate",
            "PSI and KS are descriptive monitoring signals; no customer action or automated promotion",
        ],
    }
    (ROOT / "reports/drift-validation.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "passed": passed,
                "baseline_review": baseline["review_required"],
                "shift_review": measured["review_required"],
                "tenant_isolation": isolated,
            },
            sort_keys=True,
        )
    )
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
