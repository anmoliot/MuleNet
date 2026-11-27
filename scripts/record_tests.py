"""Execute pytest and persist measured test outcomes, including failures/skips."""

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_service"))
from mulenet_core.environment import package_version


def sources():
    paths = [
        p
        for directory in ("ml_service", "scripts")
        for p in (ROOT / directory).rglob("*.py")
        if "__pycache__" not in p.parts
    ]
    paths += [ROOT / name for name in ("pyproject.toml", "uv.lock", ".python-version", ".gitleaks.toml")]
    return {
        str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--coverage", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("paths", nargs="*", default=["ml_service/tests"])
    args = parser.parse_args()
    if not args.phase.replace("-", "").isalnum():
        parser.error("Phase must be a plain identifier")
    with tempfile.TemporaryDirectory(prefix="mulenet-tests-") as directory:
        before = sources()
        xml = Path(directory) / "junit.xml"
        coverage = Path(directory) / "coverage.json"
        command = [sys.executable, "-m", "pytest", *args.paths, "-q", "-o", "junit_family=legacy", f"--junitxml={xml}"]
        if args.coverage:
            command += ["--cov", f"--cov-report=json:{coverage}", "--cov-report=term-missing"]
        result = subprocess.run(command, cwd=ROOT, check=False)
        report = {
            "phase": args.phase,
            "exit_code": result.returncode,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "cases": [],
        }
        report["source_sha256"] = before
        report["command"] = [part for part in command if not part.startswith(("--junitxml=", "--cov-report=json:"))]
        report["source_unchanged_during_run"] = before == sources()
        report["environment"] = {
            "python": platform.python_version(),
            "packages": {
                name: package_version(name)
                for name in ("numpy", "scikit-learn", "xgboost", "torch", "torch-geometric", "fastapi")
            },
        }
        if not report["source_unchanged_during_run"]:
            report["exit_code"] = 1
        if args.coverage:
            report["coverage"] = json.loads(coverage.read_bytes()) if coverage.exists() else None
            if not report["coverage"]:
                report["exit_code"] = 1
            else:
                below = [
                    name
                    for name, value in report["coverage"]["files"].items()
                    if value["summary"]["percent_covered"] < 80
                ]
                report["coverage_files_below_gate"] = below
                if below:
                    report["exit_code"] = 1
        if xml.exists():
            for case in ET.parse(xml).findall(".//testcase"):
                status = (
                    "failed"
                    if case.find("failure") is not None or case.find("error") is not None
                    else "skipped"
                    if case.find("skipped") is not None
                    else "passed"
                )
                report[status] += 1
                report["cases"].append({"name": case.attrib["name"], "status": status})
        if report["failed"] or report["skipped"]:
            report["exit_code"] = 1
        target = args.out or ROOT / "reports" / f"{args.phase}-tests.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(
            json.dumps(
                {
                    key: value
                    for key, value in report.items()
                    if key not in {"cases", "source_sha256", "environment", "coverage", "command"}
                },
                sort_keys=True,
            )
        )
        raise SystemExit(report["exit_code"] if report["cases"] else 1)


if __name__ == "__main__":
    main()
