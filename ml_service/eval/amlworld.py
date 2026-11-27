"""Disclose statistical feasibility of label-independent complete-component cohorts."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from mulenet_core.io import canonical_json
from training.experiment import load_input, preflight_splits

ROOT = Path(__file__).resolve().parents[2]


def inspect(variant):
    path = ROOT / "data/processed" / f"{variant}-cohort.json"
    dataset = load_input("amlworld", path)
    source = json.loads(path.with_suffix(".receipt.json").read_bytes())
    profile = json.loads((ROOT / "reports" / f"profile-{variant}.json").read_bytes())
    if profile["sha256"] != source["source_sha256"]:
        raise ValueError("Source profile/cohort provenance mismatch")
    bounds = tuple(
        int(datetime.strptime(profile[key], "%Y/%m/%d %H:%M").replace(tzinfo=UTC).timestamp())
        for key in ("minimum_time", "maximum_time")
    )
    report = {"dataset": "AMLworld", "variant": variant, "data_provenance": "synthetic", "cohort": source, "splits": {}}
    for name in ("temporal", "entity"):
        split, _, _ = preflight_splits(dataset, name, horizon=86400, observation_bounds=bounds, currency="USD")
        balance = {
            part: {"n": len(getattr(split, part)), "positives": sum(row.label for row in getattr(split, part))}
            for part in ("train", "val", "test")
        }
        feasible = all(value["positives"] >= 2 and value["n"] - value["positives"] >= 2 for value in balance.values())
        report["splits"][name] = {
            "class_balance": balance,
            "label_horizon_seconds": 86400,
            "status": "statistically_feasible_pending_features" if feasible else "not_estimable",
            "reason": None
            if feasible
            else "Insufficient positive classes in the fixed, label-independent whole-component cohort; refusing to retune cohort using labels or fabricate AUC",
            "performance": None,
        }
    report["limitations"] = [
        "Full large connected-network evaluation remains unimplemented by this reference snapshot engine",
        "Cohort diagnostics are NOT AMLworld model-performance results",
        "Small-component selection excludes the main connected network and cannot certify topology generalization",
    ]
    target = ROOT / "reports" / f"metrics-amlworld-{variant}.json"
    target.write_bytes(canonical_json(report))
    print(json.dumps({"variant": variant, "splits": report["splits"]}, sort_keys=True), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=["HI-Small", "LI-Small"], required=True)
    args = parser.parse_args()
    inspect(args.variant)


if __name__ == "__main__":
    main()
