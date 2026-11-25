"""Hash the exact official sampler wheels instead of trusting an un-hashed flat index."""

import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import unquote, urljoin
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
INDEX = "https://data.pyg.org/whl/torch-2.14.0+cpu.html"


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        link = dict(attrs).get("href", "")
        filename = unquote(link.rsplit("/", 1)[-1])
        if tag == "a" and filename.startswith("pyg_lib-0.9.0+pt214cpu-cp310-abi3-"):
            self.urls.append(urljoin(INDEX, link))


def main():
    parser = Links()
    with urlopen(INDEX, timeout=60) as response:
        parser.feed(response.read().decode())
    results = []
    for url in sorted(set(parser.urls)):
        digest, length = hashlib.sha256(), 0
        with urlopen(url, timeout=60) as response:
            for block in iter(lambda: response.read(1024 * 1024), b""):
                digest.update(block)
                length += len(block)
        results.append({"url": url, "sha256": digest.hexdigest(), "bytes": length})
    if not results or not any("win_amd64" in r["url"] for r in results) or not any("x86_64" in r["url"] for r in results):
        raise RuntimeError("Required official CPU sampler wheels are unavailable")
    (ROOT / "reports/sampler-wheels.json").write_text(json.dumps({"official_index": INDEX, "wheels": results}, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print("PASS: exact official sampler wheel sizes and SHA-256 receipts recorded")


if __name__ == "__main__":
    main()
