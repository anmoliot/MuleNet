"""Run Phase 1 acceptance and generate its reproducible, non-performance receipt."""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_service"))

from mulenet_core.io import canonical_json  # noqa: E402
from mulenet_core.schema import feature_schema_hash  # noqa: E402
from simulation.generator import generate  # noqa: E402


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mulenet-acceptance-") as temporary:
        junit = Path(temporary) / "tests.xml"
        command = [
            sys.executable,
            "-m",
            "pytest",
            "ml_service/tests",
            "-q",
            "-o",
            "junit_family=legacy",
            f"--junitxml={junit}",
        ]
        result = subprocess.run(command, cwd=ROOT, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
        xml = ET.parse(junit)
        cases = xml.findall(".//testcase")
        skipped = sum(case.find("skipped") is not None for case in cases)
        failed = sum(case.find("failure") is not None or case.find("error") is not None for case in cases)
        if not cases or skipped or failed:
            raise RuntimeError("Foundation acceptance requires all tests to run and pass, with no skips")
        parity = xml.find(".//property[@name='parity_points']")
        if parity is None or int(parity.attrib["value"]) < 1000:
            raise RuntimeError("Missing randomized parity evidence")
        generated = generate()
        other = generate()
        payload = canonical_json(generated.model_dump(mode="json"))
        if payload != canonical_json(other.model_dump(mode="json")):
            raise RuntimeError("Generator output is not byte-reproducible")
        sources = sorted(
            set(
                list((ROOT / "ml_service/mulenet_core").glob("*.py"))
                + list((ROOT / "ml_service/simulation").glob("*.py"))
                + list((ROOT / "ml_service/tests").glob("test_*.py"))
                + [
                    ROOT / "ml_service/feature_service.py",
                    ROOT / "ml_service/training/build_dataset.py",
                    Path(__file__).resolve(),
                    ROOT / "scripts/download_data.py",
                ]
            )
        )
        digest = hashlib.sha256()
        for source in sources:
            digest.update(source.relative_to(ROOT).as_posix().encode())
            digest.update(source.read_bytes().replace(b"\r\n", b"\n"))
        baseline = subprocess.check_output(["git", "merge-base", "main", "HEAD"], cwd=ROOT, text=True).strip()
        report = {
            "status": "passed",
            "scope": "feature-foundation-only-not-model-evaluation",
            "data_provenance": "synthetic",
            "baseline_git_sha": baseline,
            "source_sha256": digest.hexdigest(),
            "feature_schema_hash": feature_schema_hash(),
            "tests": {"passed": len(cases), "randomized_parity_points": int(parity.attrib["value"])},
            "generator": {
                "sha256": hashlib.sha256(payload).hexdigest(),
                "transactions": len(generated.transactions),
                "accounts": len(generated.accounts),
                "fraud_edges": sum(e.fraud is True for e in generated.transactions),
                "typologies": sorted({e.typology for e in generated.transactions if e.fraud}),
                "same_seed_same_bytes": True,
            },
            "environment": {
                "python": platform.python_version(),
                "system": platform.system(),
                "packages": {
                    name: importlib.metadata.version(name)
                    for name in ("pydantic", "networkx", "numpy", "scipy", "pytest", "fastapi", "httpx")
                },
            },
        }
        target = ROOT / "reports/phase1-foundation.json"
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(canonical_json(report))
        print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
