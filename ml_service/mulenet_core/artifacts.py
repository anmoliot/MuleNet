"""Verify integrity and schema before any model parser is invoked."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .io import canonical_json
from .schema import FeatureConfig, feature_schema_hash


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(directory: Path, config: FeatureConfig, data_hash: str, metrics_path: Path) -> dict[str, Any]:
    files = {
        path.name: sha256(path)
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name != "manifest.json"
    }
    manifest = {
        "format_version": 1,
        "feature_schema_hash": feature_schema_hash(config),
        "feature_config": config.model_dump(mode="json"),
        "data_hash": data_hash,
        "metrics_hash": sha256(metrics_path),
        "metrics_file": metrics_path.name,
        "files": files,
        "git_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "timestamp": datetime.now(UTC).isoformat(),
        "git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], text=True).strip()),
        "model_version": hashlib.sha256(
            canonical_json(
                {
                    name: digest
                    for name, digest in files.items()
                    if Path(name).suffix in {".ubj", ".skops", ".pt", ".ts"}
                }
            )
        ).hexdigest()[:16],
    }
    (directory / "manifest.json").write_bytes(canonical_json(manifest))
    return manifest


def verify_manifest(directory: Path, config: FeatureConfig, *, allow_synthetic: bool = False) -> dict[str, Any]:
    manifest: dict[str, Any] = json.loads((directory / "manifest.json").read_bytes())
    if not isinstance(manifest, dict):
        raise ValueError("Manifest must be a JSON object")
    if manifest.get("format_version") != 1 or manifest.get("feature_schema_hash") != feature_schema_hash(config):
        raise ValueError("Model feature-schema mismatch; explicit retraining required")
    if not manifest.get("files"):
        raise ValueError("Empty model manifest")
    for name, expected in manifest["files"].items():
        if Path(name).name != name or name.endswith((".pkl", ".pickle", ".joblib")):
            raise ValueError("Unsafe artifact path or format")
        path = directory / name
        if path.is_symlink() or not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Artifact integrity mismatch: {name}")
    metrics_file = manifest.get("metrics_file")
    if metrics_file not in manifest["files"] or manifest.get("metrics_hash") != manifest["files"][metrics_file]:
        raise ValueError("Manifest metrics hash mismatch")
    required = {
        "tabular.ubj",
        "tabular_graph.ubj",
        "calibration.skops",
        "anomaly.skops",
        "stack.skops",
        "gnn.ts",
        "training.json",
        "drift-reference.json",
    }
    if not required <= manifest["files"].keys():
        raise ValueError("Incomplete artifact bundle")
    training = json.loads((directory / "training.json").read_bytes())
    if training["data_provenance"] == "synthetic" and training["dataset"] == "sim" and not allow_synthetic:
        raise ValueError("Demo artifacts require explicit --allow-synthetic at service startup")
    return manifest
