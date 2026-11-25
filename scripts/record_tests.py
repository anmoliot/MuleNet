"""Execute pytest and persist measured test outcomes, including failures/skips."""

import argparse
import json
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True)
    parser.add_argument("paths", nargs="*", default=["ml_service/tests"])
    args = parser.parse_args()
    if not args.phase.replace("-", "").isalnum():
        parser.error("Phase must be a plain identifier")
    with tempfile.TemporaryDirectory(prefix="mulenet-tests-") as directory:
        xml = Path(directory) / "junit.xml"
        command = [sys.executable, "-m", "pytest", *args.paths, "-q", "-o", "junit_family=legacy", f"--junitxml={xml}"]
        result = subprocess.run(command, cwd=ROOT, check=False)
        report = {"phase": args.phase, "exit_code": result.returncode, "passed": 0, "failed": 0, "skipped": 0, "cases": []}
        if xml.exists():
            for case in ET.parse(xml).findall(".//testcase"):
                status = "failed" if case.find("failure") is not None or case.find("error") is not None else "skipped" if case.find("skipped") is not None else "passed"
                report[status] += 1
                report["cases"].append({"name": case.attrib["name"], "status": status})
        target = ROOT / "reports" / f"{args.phase}-tests.json"
        target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({key: value for key, value in report.items() if key != "cases"}, sort_keys=True))
        raise SystemExit(result.returncode if report["cases"] else 1)


if __name__ == "__main__":
    main()
