"""Re-run frozen simulation evaluations and compare numerical report bytes."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    cases = (("temporal", "demo-temporal-v3"), ("entity", "demo-entity-v2"))
    result = []
    for split, artifact in cases:
        report = ROOT / "reports" / f"metrics-sim-{split}.json"
        before = hashlib.sha256(report.read_bytes()).hexdigest()
        command = [sys.executable, "-m", "eval.run_eval", "--dataset", "sim", "--split", split,
                   "--data", "../data/generated/training-demo.json", "--models", f"../artifacts/{artifact}",
                   "--out", str(report), "--allow-synthetic"]
        execution = subprocess.run(command, cwd=ROOT / "ml_service", capture_output=True, text=True)
        if execution.returncode:
            print(execution.stdout[-2000:], execution.stderr[-2000:])
            raise SystemExit(execution.returncode)
        after = hashlib.sha256(report.read_bytes()).hexdigest()
        result.append({"split": split, "before_sha256": before, "after_sha256": after, "identical": before == after})
    output = {"experiments": result, "scope": "Frozen weights and input, repeat numerical evaluation; not proof of cross-platform training identity"}
    (ROOT / "reports/evaluation-reproducibility.json").write_text(json.dumps(output, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, sort_keys=True))
    if not all(item["identical"] for item in result):
        raise SystemExit("Evaluation bytes changed")


if __name__ == "__main__":
    main()
