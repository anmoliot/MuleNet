"""Run actual Java acceptance checks and derive outcomes from Surefire XML."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wsl", action="store_true")
    parser.add_argument("--tests", default="PlatformIntegrationTest,PrivacyCodecTest,ClientContractTest,SecurityBoundaryTest")
    args = parser.parse_args()
    paths = sorted([p for p in (ROOT / "backend/src").rglob("*") if p.is_file() and p.suffix in {".java", ".properties", ".sql"}] + [ROOT / "backend/pom.xml", ROOT / "contracts/ml-openapi.json"])
    hashes = {str(path.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report_directory = ROOT / "backend/target/surefire-reports"
    prior = {p.name: (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in report_directory.glob("TEST-*.xml")}
    command = ["mvn", "-B", "-ntp", f"-Dtest={args.tests}", "clean", "test"]
    if args.wsl:
        drive = ROOT.drive[0].lower()
        location = f"/mnt/{drive}" + ROOT.as_posix()[2:] + "/backend"
        command = ["wsl", "--user", "root", "--cd", location, "--exec", "env", "JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64", *command]
    result = subprocess.run(command, cwd=ROOT / "backend", text=True, encoding="utf-8", errors="replace", stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    log = ROOT / ".tools/platform-test.log"
    log.parent.mkdir(exist_ok=True)
    log.write_text(result.stdout, encoding="utf-8")
    cases = []
    requested = set(args.tests.split(","))
    for xml in sorted(report_directory.glob("TEST-*.xml")):
        if prior.get(xml.name) == (xml.stat().st_mtime_ns, hashlib.sha256(xml.read_bytes()).hexdigest()):
            continue
        tree = ET.parse(xml)
        if tree.getroot().attrib.get("name", "").rsplit(".", 1)[-1] not in requested:
            continue
        for case in tree.findall(".//testcase"):
            status = "failed" if case.find("failure") is not None or case.find("error") is not None else "skipped" if case.find("skipped") is not None else "passed"
            cases.append({"class": case.attrib["classname"], "name": case.attrib["name"], "status": status})
    unchanged = all(hashlib.sha256(path.read_bytes()).hexdigest() == hashes[str(path.relative_to(ROOT)).replace("\\", "/")] for path in paths)
    report = {"command": command, "exit_code": result.returncode, "cases": cases,
              "test_phase_executed": bool(cases),
              "source_sha256": hashes, "source_unchanged_during_run": unchanged,
              **{status: sum(case["status"] == status for case in cases) for status in ("passed", "failed", "skipped")}}
    (ROOT / "reports/platform-tests.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("\n".join(line for line in result.stdout.splitlines() if "BUILD " in line or "Tests run:" in line)[-2000:])
    print(json.dumps({k: v for k, v in report.items() if k not in {"cases", "source_sha256", "command"}}, sort_keys=True))
    raise SystemExit(result.returncode if result.returncode else 1 if not cases or not unchanged or report["failed"] or report["skipped"] else 0)


if __name__ == "__main__":
    main()
