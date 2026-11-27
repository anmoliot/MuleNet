"""Create per-install secrets exclusively; never print or overwrite credentials."""

import argparse
import base64
import os
import secrets
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Explicitly enable local simulated demonstration profiles")
    parser.add_argument(
        "--upgrade-purpose-keys",
        action="store_true",
        help="Append missing purpose-separated keys to a file created by this tool",
    )
    parser.add_argument("--out", type=Path, default=ROOT / ".env")
    args = parser.parse_args()
    if args.upgrade_purpose_keys:
        if args.demo:
            parser.error("Upgrade preserves the existing mode; do not combine it with --demo")
        lock = args.out.with_name(args.out.name + ".upgrading")
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.close(descriptor)
            original = args.out.read_text(encoding="utf-8")
            if not original.startswith("# Generated locally;"):
                raise SystemExit("Only tool-generated installation files can be upgraded automatically")
            missing = [
                key
                for key in ("MULENET_STREAM_SECRET", "MULENET_INGESTION_SECRET")
                if not any(line.startswith(key + "=") for line in original.splitlines())
            ]
            if not missing:
                print("No missing purpose-separated keys; installation unchanged")
                return
            with args.out.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write("\n" + "\n".join(f"{key}={secrets.token_urlsafe(48)}" for key in missing) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
        finally:
            lock.unlink()
        print("Added missing purpose-separated keys; existing installation values are preserved")
        return
    values = {
        name: secrets.token_urlsafe(48)
        for name in (
            "POSTGRES_PASSWORD",
            "MULENET_DB_PASSWORD",
            "REDIS_PASSWORD",
            "MULENET_SERVICE_SECRET",
            "MULENET_STREAM_SECRET",
            "MULENET_INGESTION_SECRET",
            "MULENET_DEMO_ANALYST_PASSWORD",
            "MULENET_DEMO_SUPERVISOR_PASSWORD",
            "MULENET_DEMO_ADMIN_PASSWORD",
            "MULENET_DEMO_AUDITOR_PASSWORD",
            "KEYCLOAK_ADMIN_PASSWORD",
        )
    }
    values.update(
        {
            name: base64.b64encode(secrets.token_bytes(32)).decode()
            for name in ("MULENET_TOKEN_KEY", "MULENET_ENCRYPTION_KEY", "MULENET_DEMO_JWT_SECRET")
        }
    )
    values.update(
        {
            "POSTGRES_DB": "mulenet",
            "POSTGRES_USER": "mulenet_migrator",
            "KEYCLOAK_ADMIN": "installation-admin",
            "KAFKA_CLUSTER_ID": base64.urlsafe_b64encode(uuid.uuid4().bytes).decode().rstrip("="),
            "SPRING_PROFILES_ACTIVE": "platform,demo" if args.demo else "platform",
            "MULENET_ALLOW_SYNTHETIC": "true" if args.demo else "false",
            "MULENET_ACTIVE_MODEL": "demo-temporal-v3" if args.demo else "REQUIRED_APPROVED_MODEL",
            "MULENET_OIDC_ISSUER": "",
            "MULENET_CORS_ORIGINS": "http://localhost:3000,http://localhost:5173",
        }
    )
    try:
        fd = os.open(args.out, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise SystemExit("Refusing to overwrite existing installation secrets; rotate explicitly") from None
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("# Generated locally; do not commit, share, or paste this file.\n")
        stream.write("\n".join(f"{key}={value}" for key, value in sorted(values.items())) + "\n")
    print(f"Created {args.out.name}; secrets are not printed. Windows users must restrict its ACL to their account.")


if __name__ == "__main__":
    main()
