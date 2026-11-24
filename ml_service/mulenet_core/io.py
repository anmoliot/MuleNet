"""Strict, deterministic JSON and CSV ingestion; never substitutes demo data."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .graph import canonical_events
from .schema import Dataset, Transaction


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def write_dataset(dataset: Dataset, path: Path) -> str:
    payload = canonical_json(dataset.model_dump(mode="json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return hashlib.sha256(payload).hexdigest()


def read_dataset(path: Path, *, allow_synthetic: bool = False) -> Dataset:
    if not allow_synthetic:
        raise ValueError("Demo JSON requires explicit --allow-synthetic; use a benchmark CSV loader otherwise")
    dataset = Dataset.model_validate_json(path.read_bytes())
    canonical_events(dataset.transactions)
    return dataset


def _flag(value: str) -> bool:
    if value not in {"0", "1"}:
        raise ValueError(f"Expected binary label, got {value!r}")
    return value == "1"


def load_amlworld(path: Path) -> tuple[Transaction, ...]:
    """Keep all chronological edges; duplicate Account headers are positional."""
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        required = ("Timestamp", "From Bank", "To Bank", "Amount Paid", "Payment Currency", "Payment Format", "Is Laundering")
        if any(name not in header for name in required):
            raise ValueError("Unexpected AMLworld columns")
        account_columns = [i for i, name in enumerate(header) if name == "Account"]
        if len(account_columns) != 2:
            raise ValueError("Expected two Account columns (source and destination)")
        index = {name: header.index(name) for name in required}
        events = []
        for line, row in enumerate(reader, 2):
            if len(row) != len(header):
                raise ValueError(f"Malformed AMLworld row {line}")
            try:
                events.append(Transaction(
                    transaction_id=f"amlworld:{line}",
                    source=f"{row[index['From Bank']]}:{row[account_columns[0]]}",
                    target=f"{row[index['To Bank']]}:{row[account_columns[1]]}",
                    ts=int(datetime.strptime(row[index["Timestamp"]], "%Y/%m/%d %H:%M").replace(tzinfo=timezone.utc).timestamp()),
                    amount=float(row[index["Amount Paid"]]), currency=_currency(row[index["Payment Currency"]]),
                    kind=row[index["Payment Format"]], fraud=_flag(row[index["Is Laundering"]]),
                ))
            except (ValueError, IndexError) as exc:
                raise ValueError(f"Invalid AMLworld row {line}: {exc}") from exc
    if not events:
        raise ValueError("Empty AMLworld input")
    return canonical_events(events)


def _currency(name: str) -> str:
    mapping = {"US Dollar": "USD", "Euro": "EUR", "UK Pound": "GBP", "Rupee": "INR", "Yen": "JPY", "Yuan": "CNY", "Ruble": "RUB", "Canadian Dollar": "CAD", "Australian Dollar": "AUD", "Swiss Franc": "CHF", "Shekel": "ILS", "Saudi Riyal": "SAR", "Mexican Peso": "MXN", "Brazil Real": "BRL", "Bitcoin": "BTC"}
    if name not in mapping:
        raise ValueError(f"Unknown currency {name!r}; no implicit conversion allowed")
    return mapping[name]


def load_paysim(path: Path) -> tuple[Transaction, ...]:
    """PaySim rows are simulated transactions; balances are retrospective fields."""
    events = []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        required = {"step", "type", "amount", "nameOrig", "nameDest", "isFraud", "oldbalanceOrg", "newbalanceOrig", "oldbalanceDest", "newbalanceDest"}
        if not required <= set(reader.fieldnames or ()):
            raise ValueError("Unexpected PaySim columns")
        for line, row in enumerate(reader, 2):
            try:
                events.append(Transaction(
                    transaction_id=f"paysim:{line}", source=row["nameOrig"], target=row["nameDest"],
                    ts=int(row["step"]) * 3600, amount=float(row["amount"]), currency="XXX",
                    kind=row["type"], fraud=_flag(row["isFraud"]),
                    sender_balance_before=float(row["oldbalanceOrg"]), sender_balance_after=float(row["newbalanceOrig"]),
                    receiver_balance_before=float(row["oldbalanceDest"]), receiver_balance_after=float(row["newbalanceDest"]),
                ))
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError(f"Invalid PaySim row {line}: {exc}") from exc
    if not events:
        raise ValueError("Empty PaySim input")
    return canonical_events(events)
