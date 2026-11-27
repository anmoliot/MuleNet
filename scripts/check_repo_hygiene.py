"""Fail when retired launchers, duplicate config or stale documentation reappear."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RETIRED = (
    "render.yaml",
    "run_all.bat",
    "pytest.ini",
    ".flake8",
    "MuleNet_Kaggle_Trainer.ipynb",
    "DECISIONS.md",
    "DEMO_RUNBOOK.md",
    "FIXLOG.md",
    "METRICS_REPORT.md",
    "MODEL_CARD.md",
    "PITCH_SCRIPT.md",
)


def inspect(root):
    findings = [
        {"file": name, "reason": "retired duplicate, claim or execution path"}
        for name in RETIRED
        if (root / name).exists()
    ]
    readme = (root / "README.md").read_text(encoding="utf-8")
    for phrase in ("enterprise-grade", "direct integration", "0.0021", "49.8%", "FREEZE_IMMEDIATE"):
        if phrase.casefold() in readme.casefold():
            findings.append({"file": "README.md", "reason": f"Unsupported legacy claim: {phrase}"})
    for target in re.findall(r"\]\(([^)#]+)(?:#[^)]*)?\)", readme):
        if "://" not in target and not (root / target).is_file():
            findings.append({"file": "README.md", "reason": f"Missing local link: {target}"})
    return findings


def main():
    findings = inspect(ROOT)
    report = {
        "findings": findings,
        "passed": not findings,
        "scope": "Retired root paths and README link/claim checks; not a full credential audit",
    }
    (ROOT / "reports/repository-hygiene.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(1 if findings else 0)


if __name__ == "__main__":
    main()
