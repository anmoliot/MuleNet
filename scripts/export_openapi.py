"""Export the actual strict application contract from an explicitly selected bundle."""

import argparse
import json
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ml_service"))


def main():
    from adjacency_cache import SnapshotCache
    from mulenet_core.models import ModelBundle
    from serving import create_app

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, required=True)
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args()
    bundle = ModelBundle(args.models, allow_synthetic=args.allow_synthetic)
    # Schema construction performs no Redis operation and does not start a server.
    app = create_app(bundle=bundle, cache=SnapshotCache(None), secret=secrets.token_urlsafe(64))
    directory = ROOT / "contracts"
    directory.mkdir(exist_ok=True)
    (directory / "ml-openapi.json").write_text(
        json.dumps(app.openapi(), sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    print("PASS: exported actual /v1/score and snapshot OpenAPI contracts")


if __name__ == "__main__":
    main()
