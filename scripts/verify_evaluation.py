"""Re-run frozen simulation evaluations and compare numerical report bytes."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args()
    if not args.allow_synthetic or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}", args.run_id):
        parser.error("Require explicit --allow-synthetic and a plain run identifier")
    result = []
    for split in ("temporal", "entity"):
        artifact = f"{args.run_id}-sim-{split}"
        report = ROOT / "reports/runs" / args.run_id / f"metrics-sim-{split}.json"
        before = hashlib.sha256(report.read_bytes()).hexdigest()
        command = [
            sys.executable,
            "-m",
            "eval.run_eval",
            "--dataset",
            "sim",
            "--split",
            split,
            "--data",
            "../data/generated/training-demo.json",
            "--models",
            f"../artifacts/{artifact}",
            "--out",
            str(report),
            "--allow-synthetic",
        ]
        execution = subprocess.run(command, cwd=ROOT / "ml_service", capture_output=True, text=True, check=False)
        if execution.returncode:
            print(execution.stdout[-2000:], execution.stderr[-2000:])
            raise SystemExit(execution.returncode)
        after = hashlib.sha256(report.read_bytes()).hexdigest()
        result.append({"split": split, "before_sha256": before, "after_sha256": after, "identical": before == after})
    output = {
        "run_id": args.run_id,
        "experiments": result,
        "scope": "Frozen weights and input, repeat numerical evaluation; not proof of cross-platform training identity",
    }
    (ROOT / "reports/evaluation-reproducibility.json").write_text(
        json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(output, sort_keys=True))
    if not all(item["identical"] for item in result):
        raise SystemExit("Evaluation bytes changed")


if __name__ == "__main__":
    main()
