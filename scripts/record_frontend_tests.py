"""Record actual Node unit-test results without inventing test outcomes."""

import hashlib
import json
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node is required; frontend acceptance cannot be skipped")
    sources = sorted((ROOT / "frontend/src/platform").glob("*")) + [ROOT / "frontend/tests/platform-client.test.mjs"]
    before = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    command = [node, "--test", "--test-reporter=junit", "tests/platform-client.test.mjs"]
    result = subprocess.run(command, cwd=ROOT / "frontend", capture_output=True, text=True, check=False, timeout=60)
    tree = ET.fromstring(result.stdout)
    cases = [
        {
            "name": case.attrib["name"],
            "passed": case.find("failure") is None and case.find("error") is None and case.find("skipped") is None,
        }
        for case in tree.findall(".//testcase")
    ]
    unchanged = all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == value for name, value in before.items())
    report = {
        "command": command,
        "exit_code": result.returncode,
        "cases": cases,
        "source_sha256": before,
        "source_unchanged": unchanged,
    }
    report["pass"] = result.returncode == 0 and bool(cases) and all(case["passed"] for case in cases) and unchanged
    (ROOT / "reports/frontend-unit-tests.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"pass": report["pass"], "cases": len(cases), "source_unchanged": unchanged}))
    raise SystemExit(0 if report["pass"] else 1)


if __name__ == "__main__":
    main()
