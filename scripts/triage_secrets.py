"""Classify reviewed historical defaults and cryptographically verified source digests."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
HISTORICAL_DEFAULTS = {
    "b1bdec80c6abb0ccaf6a32cab1ba9dd86f5e3a57:.env.example:generic-api-key:15",
    "5fa54036f6a05a571f3c27e9fa1669bfac2d9fed:backend/src/main/java/com/mulenet/api/config/JwtUtil.java:generic-api-key:28",
    "5fa54036f6a05a571f3c27e9fa1669bfac2d9fed:backend/src/test/resources/application.properties:generic-api-key:21",
}
PYTHON_PUBLIC_GPG_FINGERPRINT = "7169605F62C751356D054A26A821E680E5FA6305"


def public_fingerprint_finding(finding):
    if finding["RuleID"] != "generic-api-key" or finding["File"] != "reports/trivy-ml.json":
        return False
    try:
        content = blob(finding["Commit"], finding["File"])
        report = json.loads(content)
        line = content.decode().splitlines()[finding["StartLine"] - 1].strip().removesuffix(",")
        value = f"GPG_KEY={PYTHON_PUBLIC_GPG_FINGERPRINT}"
        config = report["Metadata"]["ImageConfig"]
        if line == json.dumps(value):
            return value in config["config"]["Env"]
        if line == f'"created_by": "ENV {value}"':
            return any(item.get("created_by") == f"ENV {value}" for item in config["history"])
    except (ValueError, KeyError, IndexError, TypeError, subprocess.CalledProcessError):
        return False
    return False


def blob(commit, path):
    if not re.fullmatch(r"[a-f0-9]{40}", commit) or path.startswith(("/", "-")) or ".." in Path(path).parts:
        raise ValueError("Invalid scanner object reference")
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT, stderr=subprocess.DEVNULL)


def checksum_finding(finding):
    if finding["RuleID"] != "generic-api-key" or not re.fullmatch(r"reports/[a-z-]+-tests\.json", finding["File"]):
        return False
    try:
        content = blob(finding["Commit"], finding["File"])
        report = json.loads(content)
        line = content.decode().splitlines()[finding["StartLine"] - 1].strip().removesuffix(",")
        pair = json.loads("{" + line + "}")
        if len(pair) != 1:
            return False
        source, digest = next(iter(pair.items()))
        if not re.fullmatch(r"[a-f0-9]{64}", digest) or report.get("source_sha256", {}).get(source) != digest:
            return False
        original = blob(finding["Commit"], source)
        lf = original.replace(b"\r\n", b"\n")
        return digest in {hashlib.sha256(value).hexdigest() for value in (original, lf, lf.replace(b"\n", b"\r\n"))}
    except (ValueError, KeyError, IndexError, TypeError, subprocess.CalledProcessError):
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "reports/gitleaks-history.json")
    parser.add_argument("--out", type=Path, default=ROOT / "reports/gitleaks-triage.json")
    args = parser.parse_args()
    findings = json.loads(args.input.read_bytes())
    results = []
    for finding in findings:
        if checksum_finding(finding):
            status = "verified_source_checksum_false_positive"
        elif public_fingerprint_finding(finding):
            status = "official_python_public_gpg_fingerprint"
        elif finding["Fingerprint"] in HISTORICAL_DEFAULTS:
            status = "historical_default_retired_rotate_existing_installations"
        else:
            status = "untriaged_blocking"
        results.append({key: finding[key] for key in ("RuleID", "File", "StartLine", "Commit", "Fingerprint")} | {"status": status})
    report = {"findings": results, "untriaged": sum(row["status"] == "untriaged_blocking" for row in results),
              "public_fingerprint_source": "https://github.com/docker-library/python/blob/master/3.13/slim-trixie/Dockerfile",
              "history_rewritten": False, "external_installation_rotation_verified": False,
              "current_control": "Legacy signer removed; independent generated per-install signing keys required; old IDP users must be revoked by existing operators"}
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"findings": len(results), "untriaged": report["untriaged"], "external_installation_rotation_verified": False}, sort_keys=True))
    if report["untriaged"]:
        raise SystemExit("Untriaged secret findings block the security gate")


if __name__ == "__main__":
    main()
