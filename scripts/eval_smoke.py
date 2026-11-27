"""Train/evaluate fresh seeded candidates and compare generated numerical evidence."""

import argparse
import hashlib
import json
import math
import platform
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_service"))

from eval.run_eval import evaluate
from mulenet_core.environment import package_version
from mulenet_core.io import canonical_json, write_dataset
from mulenet_core.schema import FeatureConfig, feature_schema_hash
from simulation.generator import SimulationConfig, generate
from training.experiment import train_experiment


def differences(expected, actual, path="root", *, atol=1e-6, rtol=1e-5):
    if isinstance(expected, dict) and isinstance(actual, dict):
        if expected.keys() != actual.keys():
            return [f"{path}: object keys differ"]
        return [
            failure
            for key in expected
            for failure in differences(expected[key], actual[key], f"{path}.{key}", atol=atol, rtol=rtol)
        ]
    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return [f"{path}: list lengths differ"]
        return [
            failure
            for i, (left, right) in enumerate(zip(expected, actual, strict=True))
            for failure in differences(left, right, f"{path}[{i}]", atol=atol, rtol=rtol)
        ]
    if type(expected) is not type(actual):
        return [f"{path}: value types differ"]
    if isinstance(expected, float):
        return [] if math.isclose(expected, actual, abs_tol=atol, rel_tol=rtol) else [f"{path}: {actual} != {expected}"]
    return [] if expected == actual else [f"{path}: values differ"]


def run(directory, *, allow_synthetic):
    if not allow_synthetic:
        raise ValueError("Smoke simulation requires explicit --allow-synthetic")
    config = SimulationConfig(components=6, accounts_per_component=10, days=18, noise_events_per_day=2)
    ledger = []
    dataset = generate(config, ledger)
    data_path = directory / "smoke.json"
    digest = write_dataset(dataset, data_path)
    data_path.with_suffix(".cashouts.json").write_bytes(canonical_json({"data_hash": digest, "events": ledger}))
    result = {
        "data_provenance": "synthetic",
        "data_hash": digest,
        "feature_schema_hash": feature_schema_hash(),
        "splits": {},
    }
    for split in ("temporal", "entity"):
        candidate = directory / split
        train_experiment(dataset, "sim", split, candidate, FeatureConfig(), epochs=2)
        report = evaluate("sim", data_path, split, candidate, directory / f"metrics-{split}.json", True)
        result["splits"][split] = {
            "operating_model": report["metadata"]["operating_model"],
            "models": report["models"],
            "typology": report["typology"],
            "adversarial": report["adversarial"],
            "time_to_detect": report["time_to_detect"],
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument(
        "--update-golden", action="store_true", help="Explicitly regenerate the reviewed golden; never used by CI"
    )
    parser.add_argument("--out", type=Path, default=ROOT / "reports/eval-smoke.json")
    args = parser.parse_args()
    golden = ROOT / "reports/golden/eval-smoke.json"
    if not args.allow_synthetic:
        parser.error("Pass --allow-synthetic for this explicitly simulated check")
    if not args.update_golden and not golden.is_file():
        parser.error("Golden evidence is missing; it must be explicitly generated and reviewed")
    with tempfile.TemporaryDirectory(prefix="mulenet-eval-") as temporary:
        measurement = run(Path(temporary), allow_synthetic=True)
    failures = [] if args.update_golden else differences(json.loads(golden.read_bytes()), measurement)
    if args.update_golden:
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_bytes(canonical_json(measurement))
    report = {
        "measurement": measurement,
        "passed": not failures,
        "differences": failures,
        "golden_updated": args.update_golden,
        "golden_sha256": hashlib.sha256(golden.read_bytes()).hexdigest(),
        "tolerance": {"absolute": 1e-6, "relative": 1e-5},
        "scope": "Fresh CPU training and held-out evaluation; no production-effectiveness claim",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.system(),
            "packages": {
                name: package_version(name) for name in ("torch", "torch-geometric", "numpy", "scikit-learn", "xgboost")
            },
        },
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(canonical_json(report))
    print(
        json.dumps(
            {"passed": not failures, "golden_updated": args.update_golden, "differences": failures[:10]}, sort_keys=True
        )
    )
    raise SystemExit(0 if not failures else 1)


if __name__ == "__main__":
    main()
