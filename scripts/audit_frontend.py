"""Run npm's lockfile advisory audit and retain its machine-readable result."""

import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm is required; no skipped security audit")
    result = subprocess.run(
        [npm, "audit", "--json"],
        cwd=ROOT / "frontend",
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        timeout=180,
    )
    report = json.loads(result.stdout)
    (ROOT / "reports/npm-audit.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "exit_code": result.returncode,
                "summary": report.get("metadata", {}).get("vulnerabilities"),
                "error": report.get("error"),
            },
            sort_keys=True,
        )
    )
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
