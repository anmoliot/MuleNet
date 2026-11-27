"""Audit locked runtime and explicit upstream equivalents of official CPU variants."""

import argparse
import importlib.metadata as metadata
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

from packaging.version import Version

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uv", default=shutil.which("uv"))
    args = parser.parse_args()
    if not args.uv:
        raise SystemExit("uv is required for lockfile export")
    lock = tomllib.loads((ROOT / "uv.lock").read_text(encoding="utf-8"))
    wheels = [w for package in lock["package"] for w in package.get("wheels", [])]
    if any(not w.get("hash", "").startswith("sha256:") for w in wheels):
        raise SystemExit("Un-hashed wheel in lockfile")
    tools = ROOT / ".tools"
    tools.mkdir(exist_ok=True)
    requirements = tools / "audit-requirements.txt"
    subprocess.run(
        [
            args.uv,
            "export",
            "--quiet",
            "--frozen",
            "--no-dev",
            "--format",
            "requirements-txt",
            "--output-file",
            str(requirements),
        ],
        cwd=ROOT,
        check=True,
    )
    main_report = ROOT / "reports/pip-audit.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip_audit",
            "--disable-pip",
            "--no-deps",
            "-r",
            str(requirements),
            "--format",
            "json",
            "--output",
            str(main_report),
        ],
        cwd=ROOT,
        check=False,
    )
    if result.returncode not in {0, 1} or not main_report.exists():
        raise SystemExit("Runtime advisory lookup failed")
    report = json.loads(main_report.read_bytes())
    mappings = []
    version = Version(metadata.version("torch"))
    if version.local == "cpu":
        mappings.append(
            {
                "installed": f"torch=={version}",
                "upstream": f"torch=={version.public}",
                "source": "official PyTorch CPU index; version advisory coverage is not a binary audit",
            }
        )
    names = metadata.packages_distributions().get("xgboost", [])
    if "xgboost-cpu" in names:
        mappings.append(
            {
                "installed": f"xgboost-cpu=={metadata.version('xgboost-cpu')}",
                "upstream": f"xgboost=={metadata.version('xgboost-cpu')}",
                "source": "official XGBoost CPU distribution; same upstream release",
            }
        )
    upstream_file = tools / "upstream-advisories.txt"
    upstream_file.write_text("\n".join(m["upstream"] for m in mappings) + "\n", encoding="utf-8")
    upstream_report = ROOT / "reports/python-upstream-audit.json"
    if mappings:
        upstream = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip_audit",
                "--disable-pip",
                "--no-deps",
                "-r",
                str(upstream_file),
                "--format",
                "json",
                "--output",
                str(upstream_report),
            ],
            cwd=ROOT,
            check=False,
        )
        if upstream.returncode not in {0, 1} or not upstream_report.exists():
            raise SystemExit("Explicit CPU upstream advisory lookup failed")
        extra = json.loads(upstream_report.read_bytes())["dependencies"]
    else:
        extra = []
    known_mapped = {m["installed"].split("==")[0] for m in mappings}
    unknown = [p for p in report["dependencies"] if p.get("skip_reason") and p["name"] not in known_mapped] + [
        p for p in extra if p.get("skip_reason")
    ]
    vulnerabilities = [
        {"name": p["name"], "version": p.get("version"), "advisory": v["id"]}
        for p in report["dependencies"] + extra
        for v in p.get("vulns", [])
    ]
    summary = {
        "cpu_variant_mappings": mappings,
        "uncovered_packages": unknown,
        "vulnerabilities": vulnerabilities,
        "hashed_wheels_checked": len(wheels),
        "scope": "Runtime and explicitly mapped upstream Python version advisories; native image/SBOM and sampler provenance checked separately",
    }
    (ROOT / "reports/python-security.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "uncovered_packages": len(unknown),
                "vulnerabilities": len(vulnerabilities),
                "hashed_wheels_checked": len(wheels),
            },
            sort_keys=True,
        )
    )
    if unknown or vulnerabilities:
        raise SystemExit("Python dependency security gate failed")


if __name__ == "__main__":
    main()
