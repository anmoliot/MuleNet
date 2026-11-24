"""Verify stored bytes, sequence and a separately witnessed audit-chain head."""

import argparse
import hashlib
import json
import os
from pathlib import Path


def verify(entries, expected_head=None, *, allow_unanchored=False):
    if not expected_head and not allow_unanchored:
        raise ValueError("An independently witnessed --expected-head is required (or explicit --allow-unanchored for diagnostics)")
    previous = "GENESIS"
    for sequence, entry in enumerate(entries, 1):
        if entry["sequence"] != sequence or entry["previous_hash"] != previous:
            raise ValueError("Audit sequence or predecessor mismatch")
        actual = hashlib.sha256((previous + "\n" + entry["payload"]).encode()).hexdigest()
        if actual != entry["entry_hash"]:
            raise ValueError("Audit payload hash mismatch")
        previous = actual
    if expected_head and expected_head != previous:
        raise ValueError("Audit head differs from external witness (including truncation)")
    return {"verified_entries": len(entries), "head": previous, "anchored": bool(expected_head),
            "scope": "Hash-chain integrity; not proof that the operator's original action was legitimate"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True, help="Unmodified JSON audit export")
    parser.add_argument("--expected-head")
    parser.add_argument("--allow-unanchored", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = verify(json.loads(args.file.read_bytes()), args.expected_head, allow_unanchored=args.allow_unanchored)
    args.out.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
