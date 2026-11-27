"""Require completed security evidence; unknown or vulnerable results fail closed."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def assess(directory):
    checks = {}
    digests = {}

    def read(name):
        path = directory / name
        content = path.read_bytes()
        digests[name] = hashlib.sha256(content).hexdigest()
        return json.loads(content)

    def tests_passed(report):
        current = report.get("source_sha256", {})
        return (
            bool(current)
            and report["exit_code"] == 0
            and report["source_unchanged_during_run"]
            and report["passed"] > 0
            and report["failed"] == report["skipped"] == 0
            and all(
                hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest for name, digest in current.items()
            )
        )

    validators = {
        "python-security.json": lambda r: not r["vulnerabilities"] and not r["uncovered_packages"],
        "npm-audit.json": lambda r: not r.get("error") and r["metadata"]["vulnerabilities"]["total"] == 0,
        "gitleaks-triage.json": lambda r: r["untriaged"] == 0,
        "unsafe-paths.json": lambda r: r["files_checked"] > 0 and not r["findings"],
        "security-python-tests.json": tests_passed,
        "platform-tests.json": tests_passed,
        "dependency-check-report.json": lambda r: (
            bool(r["dependencies"]) and not any(d.get("vulnerabilities") for d in r["dependencies"])
        ),
        "trivy-ml.json": lambda r: bool(r["Results"]) and not any(d.get("Vulnerabilities") for d in r["Results"]),
        "trivy-backend.json": lambda r: bool(r["Results"]) and not any(d.get("Vulnerabilities") for d in r["Results"]),
    }
    for name, validator in validators.items():
        try:
            checks[name] = "passed" if validator(read(name)) else "failed"
        except (OSError, KeyError, TypeError, ValueError):
            checks[name] = "missing_or_invalid"
    return {
        "checks": checks,
        "input_sha256": digests,
        "passed": all(value == "passed" for value in checks.values()),
        "scope": "Local receipt aggregation; not proof of hosted CI or production approval",
        "production_approved": False,
    }


def main():
    report = assess(ROOT / "reports")
    (ROOT / "reports/security-gate.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    raise SystemExit(0 if report["passed"] else 1)


if __name__ == "__main__":
    main()
