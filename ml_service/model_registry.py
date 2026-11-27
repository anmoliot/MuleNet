"""Small, local, read-only serving registry with explicit rollout and rollback."""

import argparse
import hashlib
import json
import os
import re
import threading
from pathlib import Path

from mulenet_core.calibration import calibrated_probabilities
from mulenet_core.io import canonical_json
from mulenet_core.models import ModelBundle


class ModelRegistry:
    def __init__(self, root, *, allow_synthetic=False):
        self.root = Path(root).resolve(strict=True)
        self.allow = allow_synthetic
        self.lock = threading.RLock()
        self.bundles = {}
        self.state = None
        self.fingerprint = None
        self.refresh()

    def candidate(self, name):
        if not isinstance(name, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,80}", name):
            raise ValueError("Invalid registry version directory")
        path = self.root / name
        if path.is_symlink() or path.resolve(strict=True).parent != self.root:
            raise ValueError("Registry version escapes trusted root")
        if not (path / "evaluation.json").is_file():
            raise ValueError("Registry promotion requires measured evaluation evidence")
        bundle = ModelBundle(path, allow_synthetic=self.allow)
        if bundle.training["data_provenance"] == "synthetic" and not self.allow:
            raise ValueError("Registry candidates require explicit --allow-synthetic for simulation")
        if bundle.training.get("selected_model", bundle.training["default_deep_path"]) != "tabular_graph":
            raise ValueError(
                "This rollout registry supports the evaluated graph-tabular path only; neural rollout requires a separate deadline worker per version"
            )
        return bundle

    def refresh(self):
        with self.lock:
            path = self.root / "registry.json"
            content = path.read_bytes()
            fingerprint = hashlib.sha256(content).hexdigest()
            if self.fingerprint == fingerprint:
                return
            state = json.loads(content)
            if set(state) != {"active", "previous", "canary", "canary_percent", "shadow"}:
                raise ValueError("Invalid registry contract")
            percent = state["canary_percent"]
            if not isinstance(percent, int) or not 0 <= percent <= 100 or (percent and not state["canary"]):
                raise ValueError("Invalid canary percentage")
            names = {name for name in (state["active"], state["previous"], state["canary"], state["shadow"]) if name}
            if not state["active"]:
                raise ValueError("Registry must have an active model")
            bundles = {name: self.candidate(name) for name in names}
            if len({b.manifest["feature_schema_hash"] for b in bundles.values()}) != 1:
                raise ValueError("Registry feature schemas differ")
            self.state, self.bundles, self.fingerprint = state, bundles, fingerprint

    @property
    def active(self):
        with self.lock:
            self.refresh()
            return self.bundles[self.state["active"]]

    def choose(self, tenant, account):
        with self.lock:
            self.refresh()
            bucket = int(hashlib.sha256(canonical_json([tenant, account])).hexdigest()[:8], 16) % 100
            name = self.state["canary"] if bucket < self.state["canary_percent"] else self.state["active"]
            return self.bundles[name]

    def shadow(self, features):
        with self.lock:
            self.refresh()
            name = self.state["shadow"]
            if not name:
                return []
            candidate = self.bundles[name]
        raw = candidate.graph_tabular.predict_proba(candidate.matrix([features]))[:, 1]
        return [
            {
                "model_version": candidate.manifest["model_version"],
                "probability": float(calibrated_probabilities(candidate.calibration["tabular_graph"], raw)[0]),
                "used_for_policy": False,
            }
        ]


def _update(root, command, version=None, percentage=0, allow_synthetic=False):
    root = Path(root)
    path = root / "registry.json"
    if command == "init":
        if path.exists():
            raise FileExistsError("Registry already exists")
        state = {"active": version, "previous": None, "canary": None, "canary_percent": 0, "shadow": None}
    else:
        state = json.loads(path.read_bytes())
        if command == "rollback":
            if not state["previous"]:
                raise ValueError("No previous version")
            state["active"], state["previous"] = state["previous"], state["active"]
            state["canary"], state["canary_percent"] = None, 0
        elif command == "promote":
            state["previous"], state["active"] = state["active"], version
            state["canary"], state["canary_percent"] = None, 0
        elif command == "canary":
            state["canary"], state["canary_percent"] = version, percentage
        elif command == "shadow":
            state["shadow"] = version
        else:
            raise ValueError("Unknown registry command")
    # Verify before atomically exposing a pointer to any serving process.
    checker = object.__new__(ModelRegistry)
    checker.root, checker.allow = root.resolve(strict=True), allow_synthetic
    for name in {v for k, v in state.items() if k != "canary_percent" and v}:
        checker.candidate(name)
    if not isinstance(state["canary_percent"], int) or not 0 <= state["canary_percent"] <= 100:
        raise ValueError("Invalid canary percentage")
    temporary = path.with_name(".registry-new.json")
    with temporary.open("xb") as stream:
        stream.write(canonical_json(state))
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    return state


def update(root, command, version=None, percentage=0, allow_synthetic=False):
    from filelock import FileLock

    with FileLock(str(Path(root) / ".registry.lock"), timeout=0):
        return _update(root, command, version, percentage, allow_synthetic)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["init", "shadow", "canary", "promote", "rollback"])
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--version")
    parser.add_argument("--percentage", type=int, default=0)
    parser.add_argument("--allow-synthetic", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(update(args.root, args.command, args.version, args.percentage, args.allow_synthetic), sort_keys=True)
    )


if __name__ == "__main__":
    main()
