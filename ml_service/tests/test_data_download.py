import json
import subprocess

import pytest

from scripts import download_data


def test_no_credentials_or_missing_cli_never_falls_back(monkeypatch, tmp_path):
    for name in ("KAGGLE_USERNAME", "KAGGLE_KEY", "KAGGLE_API_TOKEN"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("KAGGLE_CONFIG_DIR", str(tmp_path))
    with pytest.raises(RuntimeError, match="credentials absent"):
        download_data.download("amlworld", "HI-Small", "CDLA-Sharing-1.0")
    monkeypatch.setenv("KAGGLE_API_TOKEN", "test-only-not-a-real-token")
    monkeypatch.setattr(download_data.shutil, "which", lambda _: None)
    with pytest.raises(RuntimeError, match="CLI missing"):
        download_data.download("amlworld", "HI-Small", "CDLA-Sharing-1.0")
    with pytest.raises(ValueError, match="license"):
        download_data.download("amlworld", "HI-Small", "Apache-2.0")
    with pytest.raises(ValueError, match="variant"):
        download_data.download("amlworld", "other", "CDLA-Sharing-1.0")


def test_download_receipt_hashes_output_and_propagates_failures(monkeypatch, tmp_path):
    monkeypatch.setattr(download_data, "ROOT", tmp_path)
    monkeypatch.setattr(download_data, "has_credentials", lambda: True)
    monkeypatch.setattr(download_data.shutil, "which", lambda _: "kaggle")
    calls = []

    def fake_download(args, **kwargs):
        calls.append(args)
        output = download_data.Path(args[args.index("-p") + 1])
        if "metadata" in args:
            (output / "dataset-metadata.json").write_text('{"licenses":[{"name":"CDLA-Sharing-1.0"}]}', encoding="utf-8")
        else:
            (output / "HI-Small_Trans.csv").write_text("fixture-not-benchmark-data\n", encoding="utf-8")

    monkeypatch.setattr(download_data.subprocess, "run", fake_download)
    result = download_data.download("amlworld", "HI-Small", "CDLA-Sharing-1.0")
    assert result["sha256"] == download_data.file_hash(tmp_path / "data/raw/amlworld/HI-Small_Trans.csv")
    assert json.loads((tmp_path / "reports/data-amlworld-HI-Small.json").read_text()) == result
    assert len(calls) == 2
    with pytest.raises(FileExistsError):
        download_data.download("amlworld", "HI-Small", "CDLA-Sharing-1.0")

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, "kaggle")

    monkeypatch.setattr(download_data.subprocess, "run", fail)
    with pytest.raises(subprocess.CalledProcessError):
        download_data.download("amlworld", "LI-Small", "CDLA-Sharing-1.0")
    assert not (tmp_path / "reports/data-amlworld-LI-Small.json").exists()
