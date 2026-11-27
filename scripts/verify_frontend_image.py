"""Exercise the actual read-only, non-root frontend image, including CSP injection rejection."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wsl", action="store_true")
    parser.add_argument("--image", default="mulenet/frontend:local")
    args = parser.parse_args()
    prefix = ["wsl", "--user", "root", "--exec", "docker"] if args.wsl else ["docker"]

    def docker(*command, check=True):
        result = subprocess.run([*prefix, *command], capture_output=True, text=True, check=False, timeout=90)
        if check and result.returncode:
            raise RuntimeError(f"Docker check failed: {result.stderr[-2000:]}")
        return result

    sources = [ROOT / "frontend" / name for name in ("Dockerfile", "nginx.conf", "nginx-main.conf", "start-nginx.sh")]
    before = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    container = None
    try:
        image = json.loads(docker("image", "inspect", args.image).stdout)[0]
        assert image["Config"]["User"] == "101:101"
        options = [
            "--read-only",
            "--network",
            "none",
            "--tmpfs",
            "/tmp",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--add-host",
            "backend:127.0.0.1",
        ]
        container = docker(
            "run", "-d", *options, "-e", "MULENET_OIDC_BROWSER_ORIGIN=https://identity.example.test", args.image
        ).stdout.strip()
        result = None
        for _ in range(20):
            result = docker(
                "exec", container, "wget", "-S", "-O", "-", "http://127.0.0.1:8080/?code=fixture-log-probe", check=False
            )
            if result.returncode == 0:
                break
            time.sleep(0.25)
        assert result is not None and result.returncode == 0
        assert "MuleNet | Investigator Console" in result.stdout
        assert "Content-Security-Policy" in result.stderr
        assert "connect-src 'self' https://identity.example.test" in result.stderr
        assert "X-Content-Type-Options: nosniff" in result.stderr
        assert "fixture-log-probe" not in docker("logs", container).stdout
        docker("exec", container, "nginx", "-t")
        rejected = docker(
            "run",
            "--rm",
            *options,
            "-e",
            "MULENET_OIDC_BROWSER_ORIGIN=https://identity.example; injected",
            args.image,
            check=False,
        )
        assert rejected.returncode != 0 and "Invalid explicit OIDC browser origin" in rejected.stderr
        newline = docker(
            "run",
            "--rm",
            *options,
            "-e",
            "MULENET_OIDC_BROWSER_ORIGIN=https://identity.example\ninjected",
            args.image,
            check=False,
        )
        assert newline.returncode != 0 and "Invalid explicit OIDC browser origin" in newline.stderr
        assert all(
            hashlib.sha256(path.read_bytes()).hexdigest() == before[str(path.relative_to(ROOT))] for path in sources
        )
        report = {
            "pass": True,
            "image_id": image["Id"],
            "runtime_user": image["Config"]["User"],
            "read_only": True,
            "network": "none",
            "capabilities_dropped": "ALL",
            "headers_verified": True,
            "query_logging_scrubbed": True,
            "invalid_csp_origin_rejected": True,
            "source_sha256": before,
            "scope": "Actual static container smoke; does not certify OIDC login, live API proxy or vulnerability freedom",
        }
        (ROOT / "reports/frontend-image.json").write_text(
            json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({name: value for name, value in report.items() if name != "source_sha256"}))
    finally:
        if container:
            docker("rm", "-f", container, check=False)


if __name__ == "__main__":
    main()
