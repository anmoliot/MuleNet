"""Generate actual dataset inventory and originator-repetition evidence."""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.download_data import file_hash


def profile(path: Path, paysim: bool):
    senders, receivers = set(), set()
    rows, flagged = 0, 0
    minimum, maximum = None, None
    currencies, kinds = Counter(), Counter()
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        for row in reader:
            if len(row) != len(header):
                raise ValueError("Malformed dataset row; refusing to silently skip")
            if paysim:
                step, kind, _, sender, _, _, target, _, _, flag, _ = row
                ts = int(step)
                currency = "XXX"
            else:
                ts, bank_from, account_from, bank_to, account_to, _, _, _, currency, kind, flag = row
                sender, target = bank_from + ":" + account_from, bank_to + ":" + account_to
            if flag not in {"0", "1"}:
                raise ValueError("Unknown label")
            senders.add(sender)
            receivers.add(target)
            rows += 1
            flagged += int(flag)
            minimum = ts if minimum is None or ts < minimum else minimum
            maximum = ts if maximum is None or ts > maximum else maximum
            currencies[currency] += 1
            kinds[kind] += 1
    return {"file": path.name, "sha256": file_hash(path), "data_provenance": "synthetic",
            "transactions": rows, "flagged_transactions": flagged, "unique_originators": len(senders),
            "unique_destinations": len(receivers), "accounts": len(senders | receivers),
            "originator_unique_per_transaction": len(senders) / rows, "minimum_time": minimum, "maximum_time": maximum,
            "currencies": dict(sorted(currencies.items())), "kinds": dict(sorted(kinds.items()))}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=["paysim", "HI-Small", "LI-Small", "all"], default="all")
    args = parser.parse_args()
    paths = {"paysim": ROOT / "data/raw/paysim/PS_20174392719_1491204439457_log.csv",
             "HI-Small": ROOT / "data/raw/amlworld/HI-Small_Trans.csv", "LI-Small": ROOT / "data/raw/amlworld/LI-Small_Trans.csv"}
    for name, path in paths.items():
        if args.dataset in {name, "all"}:
            result = profile(path, name == "paysim")
            output = ROOT / "reports" / f"profile-{name}.json"
            output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(result, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
