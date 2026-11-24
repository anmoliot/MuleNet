"""Assemble evaluation artifacts without inventing absent measurements."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    reports = ROOT / "reports"
    experiments = {name: json.loads((reports / f"metrics-{name}.json").read_bytes()) for name in ("sim-temporal", "sim-entity", "paysim-temporal", "amlworld-HI-Small", "amlworld-LI-Small")}
    (reports / "metrics.json").write_text(json.dumps({"experiments": experiments, "production_approved": False, "scope": "Explicitly disclosed simulations, diagnostics and non-estimable primary cohorts"}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    for section in ("ablation", "typology", "adversarial", "calibration"):
        results = {name: json.loads((reports / f"{section}-{name}.json").read_bytes()) for name in ("sim-temporal", "sim-entity")}
        (reports / f"{section}.json").write_text(json.dumps(results, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("PASS: assembled measured report sections; production_approved=false; primary non-estimability retained")


if __name__ == "__main__":
    main()
