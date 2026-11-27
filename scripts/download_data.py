"""Fetch only named benchmark files after local authentication/license consent."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASETS = {
    "amlworld": (
        "ealtman2019/ibm-transactions-for-anti-money-laundering-aml",
        {"HI-Small": "HI-Small_Trans.csv", "LI-Small": "LI-Small_Trans.csv"},
    ),
    "paysim": ("ealaxi/paysim1", {"default": "PS_20174392719_1491204439457_log.csv"}),
}


def has_credentials() -> bool:
    config_dir = Path(os.environ.get("KAGGLE_CONFIG_DIR", str(Path.home() / ".kaggle")))
    return bool(
        os.environ.get("KAGGLE_API_TOKEN")
        or (os.environ.get("KAGGLE_USERNAME") and os.environ.get("KAGGLE_KEY"))
        or (config_dir / "kaggle.json").is_file()
    )


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def download(dataset: str, variant: str, license_id: str) -> dict[str, str]:
    slug, files = DATASETS[dataset]
    if variant not in files:
        raise ValueError(f"Unsupported variant {variant!r}; choose from {tuple(files)}")
    if not license_id.strip():
        raise ValueError("Read the supplier terms and pass --license-acknowledged LICENSE_ID")
    if dataset == "amlworld" and license_id != "CDLA-Sharing-1.0":
        raise ValueError("IBM distinguishes data license CDLA-Sharing-1.0 from its code license")
    if not has_credentials():
        raise RuntimeError(
            "Kaggle credentials absent. Authenticate locally or supply authorized CSV paths; never paste credentials into chat."
        )
    executable = shutil.which("kaggle")
    if executable is None:
        raise RuntimeError("Kaggle CLI missing; install the official kaggle package. No synthetic fallback.")
    destination = ROOT / "data" / "raw" / dataset
    destination.mkdir(parents=True, exist_ok=True)
    filename = files[variant]
    target = destination / filename
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}; reuse its recorded hash or remove it explicitly")
    # A staging directory keeps interrupted downloads from looking like valid input.
    with tempfile.TemporaryDirectory(prefix="download-", dir=destination) as temporary:
        staging = Path(temporary)
        subprocess.run([executable, "datasets", "metadata", slug, "-p", str(staging)], check=True, timeout=120)
        metadata = staging / "dataset-metadata.json"
        if not metadata.is_file():
            raise RuntimeError("Supplier metadata missing; no verified download receipt can be written")
        supplier = json.loads(metadata.read_text(encoding="utf-8"))
        if not supplier.get("licenses"):
            raise RuntimeError("Supplier metadata lacks license terms; review licensing before proceeding")

        def normalized(value):
            return "".join(character for character in value.casefold() if character.isalnum())

        supplier_licenses = {
            normalized(item["name"])
            for item in supplier["licenses"]
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        }
        if normalized(license_id) not in supplier_licenses:
            raise RuntimeError("Acknowledged license differs from supplier metadata; resolve licensing explicitly")
        subprocess.run(
            [executable, "datasets", "download", "-d", slug, "-f", filename, "-p", str(staging), "--unzip"],
            check=True,
            timeout=3600,
        )
        incoming = staging / filename
        if not incoming.is_file() or incoming.stat().st_size == 0:
            raise RuntimeError("Requested CSV missing or empty after download")
        receipt = {
            "dataset": dataset,
            "variant": variant,
            "source": slug,
            "data_provenance": "synthetic",
            "sha256": file_hash(incoming),
            "supplier_metadata_sha256": file_hash(metadata),
            "operator_acknowledged_license": license_id,
        }
        # Retain the actual metadata locally; the receipt identifies it by hash.
        metadata.replace(destination / f"{variant}-supplier-metadata.json")
        incoming.replace(target)
    report = ROOT / "reports" / f"data-{dataset}-{variant}.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def download_public(dataset: str, variant: str, license_id: str) -> dict:
    slug, files = DATASETS[dataset]
    if variant not in files:
        raise ValueError("Unsupported dataset variant")
    aliases = {
        "CC-BY-SA-4.0": "CC BY-SA 4.0",
        "CDLA-Sharing-1.0": "Community Data License Agreement - Sharing - Version 1.0",
    }
    if license_id not in aliases:
        raise ValueError("Explicit supported supplier-license acknowledgment required")
    with urllib.request.urlopen(f"https://www.kaggle.com/api/v1/datasets/view/{slug}", timeout=60) as response:
        metadata = json.load(response)
    if metadata.get("isPrivate") or metadata.get("licenseName") != aliases[license_id]:
        raise ValueError("Supplier visibility/license differs from the acknowledged terms")
    filename = files[variant]
    directory = ROOT / "data/raw" / dataset
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    if target.exists():
        raise FileExistsError(f"Refusing to overwrite {target}")
    version = metadata["currentVersionNumber"]
    query = urllib.parse.urlencode({"fileName": filename, "datasetVersionNumber": version})
    url = f"https://www.kaggle.com/api/v1/datasets/download/{slug}?{query}"
    with tempfile.TemporaryDirectory(prefix="public-download-", dir=directory) as temporary:
        staging = Path(temporary)
        raw = staging / "response"
        with urllib.request.urlopen(url, timeout=120) as response, raw.open("wb") as output:
            size = 0
            while chunk := response.read(1024 * 1024):
                size += len(chunk)
                if size > 1024**3:
                    raise ValueError("Download exceeds single-small-file byte budget")
                output.write(chunk)
        if zipfile.is_zipfile(raw):
            with zipfile.ZipFile(raw) as archive:
                member = archive.getinfo(filename)
                if member.file_size > 1024**3:
                    raise ValueError("Uncompressed dataset exceeds byte budget")
                with archive.open(member) as source, (staging / filename).open("wb") as output:
                    shutil.copyfileobj(source, output)
            incoming = staging / filename
        else:
            incoming = raw
        if incoming.stat().st_size == 0:
            raise ValueError("Empty download")
        with incoming.open("rb") as stream:
            if b"," not in stream.readline(4096):
                raise ValueError("Provider response is not a CSV")
        metadata_bytes = (json.dumps(metadata, sort_keys=True) + "\n").encode()
        (directory / f"{variant}-supplier-metadata.json").write_bytes(metadata_bytes)
        receipt = {
            "dataset": dataset,
            "variant": variant,
            "source": slug,
            "supplier_version": version,
            "data_provenance": "synthetic",
            "license": license_id,
            "sha256": file_hash(incoming),
            "supplier_metadata_sha256": hashlib.sha256(metadata_bytes).hexdigest(),
            "bytes": incoming.stat().st_size,
        }
        incoming.replace(target)
    report = ROOT / "reports" / f"data-{dataset}-{variant}.json"
    report.parent.mkdir(exist_ok=True)
    report.write_text(json.dumps(receipt, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=DATASETS, required=True)
    parser.add_argument("--variant", required=True)
    parser.add_argument("--license-acknowledged", required=True, metavar="LICENSE_ID")
    parser.add_argument(
        "--public", action="store_true", help="Use the supplier's public versioned endpoint without credentials"
    )
    args = parser.parse_args()
    try:
        method = download_public if args.public else download
        print(json.dumps(method(args.dataset, args.variant, args.license_acknowledged), sort_keys=True))
    except (ValueError, RuntimeError, OSError, subprocess.SubprocessError) as exc:
        parser.exit(1, f"Download refused: {exc}\n")


if __name__ == "__main__":
    main()
