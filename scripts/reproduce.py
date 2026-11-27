"""Explicit research reproduction; never substitute a simulator for a benchmark."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_service"))
sys.path.insert(0, str(ROOT))

from mulenet_core.artifacts import sha256
from mulenet_core.io import canonical_json, read_dataset, write_dataset
from mulenet_core.schema import FeatureConfig
from simulation.generator import SimulationConfig, generate

from scripts.download_data import DATASETS


def benchmark_input(dataset, variant):
    if variant not in DATASETS[dataset][1]:
        raise ValueError("Unsupported benchmark variant")
    path = ROOT / "data/raw" / dataset / DATASETS[dataset][1][variant]
    receipt = json.loads((ROOT / "reports" / f"data-{dataset}-{variant}.json").read_bytes())
    if not path.is_file() or sha256(path) != receipt["sha256"]:
        raise ValueError("Benchmark missing or hash mismatch; acquire authorized data with download_data.py")
    metadata = path.parent / f"{variant}-supplier-metadata.json"
    if sha256(metadata) != receipt["supplier_metadata_sha256"]:
        raise ValueError("Supplier metadata missing or changed")
    return path, receipt


def simulator_data(*, allow_synthetic):
    if not allow_synthetic:
        raise ValueError("Simulator reproduction requires explicit --allow-synthetic")
    ledger = []
    dataset = generate(
        SimulationConfig(components=6, accounts_per_component=10, days=18, noise_events_per_day=2), ledger
    )
    path = ROOT / "data/generated/training-demo.json"
    content = canonical_json(dataset.model_dump(mode="json"))
    cashouts = canonical_json(
        {"data_hash": hashlib.sha256(content).hexdigest(), "data_provenance": "synthetic", "events": ledger}
    )
    ledger_path = path.with_suffix(".cashouts.json")
    for target, expected in ((path, content), (ledger_path, cashouts)):
        if target.exists() and target.read_bytes() != expected:
            # Existing terminal ledgers may contain generator configuration metadata.
            if target == ledger_path:
                current = json.loads(target.read_bytes())
                if current.get("data_hash") == hashlib.sha256(content).hexdigest() and current.get("events") == ledger:
                    continue
            raise FileExistsError("Existing demo input differs; preserve it and explicitly select another workspace")
    digest = write_dataset(dataset, path)
    if not ledger_path.exists():
        ledger_path.write_bytes(cashouts)
    return path, {"data_provenance": "synthetic", "sha256": digest}


def execute(action, dataset, *, allow_synthetic=False, run_id="repro-v1", epochs=30):
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", run_id):
        raise ValueError("Run id must be a plain identifier")
    if action not in {"data", "train", "eval"} or dataset not in {"sim", "paysim", "amlworld"}:
        raise ValueError("Unknown action/dataset")
    if dataset == "sim":
        path, provenance = simulator_data(allow_synthetic=allow_synthetic)
    else:
        variants = ("HI-Small", "LI-Small") if dataset == "amlworld" else ("default",)
        checked = [benchmark_input(dataset, variant) for variant in variants]
        path, provenance = checked[0]
    destination = ROOT / "reports/runs" / run_id
    destination.mkdir(parents=True, exist_ok=True)
    if action == "data":
        result = {
            "dataset": dataset,
            "verified": True,
            "data_provenance": "synthetic",
            "inputs": [receipt for _, receipt in checked] if dataset != "sim" else [provenance],
        }
    elif dataset == "amlworld":
        raise RuntimeError(
            "Full-network AMLworld training/evaluation is not implemented. Cohort diagnostics are NOT a replacement benchmark."
        )
    elif dataset == "paysim":
        from eval.paysim import run

        from scripts.profile_datasets import profile

        profiled = profile(path, True)
        (ROOT / "reports/profile-paysim.json").write_bytes(canonical_json(profiled))
        result = run(path, ROOT / "artifacts" / f"{run_id}-paysim", train=action == "train")
    else:
        from eval.run_eval import evaluate
        from training.experiment import train_experiment

        data = read_dataset(path, allow_synthetic=True)
        candidates = [ROOT / "artifacts" / f"{run_id}-sim-{split}" for split in ("temporal", "entity")]
        if action == "train" and any(candidate.exists() for candidate in candidates):
            raise FileExistsError("Run candidates already exist; use a new RUN_ID. Training never overwrites weights.")
        result = {"dataset": dataset, "data_provenance": "synthetic", "splits": {}}
        for split, candidate in zip(("temporal", "entity"), candidates, strict=True):
            if action == "train":
                measured = train_experiment(data, "sim", split, candidate, FeatureConfig(), epochs=epochs)
            else:
                measured = evaluate("sim", path, split, candidate, destination / f"metrics-sim-{split}.json", True)
            result["splits"][split] = measured
    (destination / f"{action}-{dataset}.json").write_bytes(canonical_json(result))
    return {
        "action": action,
        "dataset": dataset,
        "run_id": run_id,
        "passed": True,
        "reports": destination.relative_to(ROOT).as_posix(),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["data", "train", "eval"])
    parser.add_argument("--dataset", choices=["sim", "paysim", "amlworld"], required=True)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--run-id", default="repro-v1")
    parser.add_argument("--epochs", type=int, default=30)
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("Epochs must be positive")
    try:
        result = execute(
            args.action, args.dataset, allow_synthetic=args.allow_synthetic, run_id=args.run_id, epochs=args.epochs
        )
    except (OSError, ValueError, RuntimeError) as exc:
        parser.exit(1, f"Reproduction refused: {exc}\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
