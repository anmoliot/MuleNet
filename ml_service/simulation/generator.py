"""Seeded typology/camouflage generator with opaque, non-label-derived IDs."""

from __future__ import annotations

import argparse
import random
from collections import defaultdict
from itertools import pairwise
from pathlib import Path

from mulenet_core.graph import canonical_events
from mulenet_core.io import write_dataset
from mulenet_core.schema import Account, Dataset, StrictModel, Transaction
from pydantic import Field, model_validator

TYPOLOGIES = (
    "fan_in",
    "fan_out",
    "scatter_gather",
    "cycle",
    "layering",
    "pass_through",
    "dormant_activation",
    "structuring",
)


class SimulationConfig(StrictModel):
    seed: int = 42
    components: int = Field(default=12, ge=3, le=1000)
    accounts_per_component: int = Field(default=12, ge=10, le=1000)
    days: int = Field(default=30, ge=7, le=365)
    layering_depth: int = Field(default=3, ge=1, le=6)
    delay_seconds: int = Field(default=120, ge=1, le=604800)
    split_count: int = Field(default=3, ge=1, le=20)
    merchant_hop: bool = False
    noise_events_per_day: int = Field(default=4, ge=0, le=1000)
    timing_jitter_seconds: int = Field(default=900, ge=0, le=86400)
    amount_noise: float = Field(default=0.15, ge=0, le=0.9, allow_inf_nan=False)
    base_time: int = Field(default=1735689600, ge=604800)
    typologies: tuple[str, ...] = TYPOLOGIES
    fraud_probability: float = Field(default=0.65, ge=0, le=1, allow_inf_nan=False)

    @model_validator(mode="after")
    def validate_structure(self) -> SimulationConfig:
        if not self.typologies or not set(self.typologies) <= set(TYPOLOGIES):
            raise ValueError("Choose supported typologies")
        if self.layering_depth > self.accounts_per_component - 7:
            raise ValueError("Not enough independent relay accounts for layering_depth")
        return self


def generate(config: SimulationConfig = SimulationConfig(), cashout_ledger: list[dict] | None = None) -> Dataset:
    rng = random.Random(config.seed)
    transactions: list[Transaction] = []
    accounts = []
    tags: dict[str, set[str]] = defaultdict(set)
    used_ids: set[str] = set()

    def new_account() -> str:
        while True:
            identifier = f"a{rng.getrandbits(64):016x}"
            if identifier not in used_ids:
                used_ids.add(identifier)
                return identifier

    def emit(
        source: str, target: str, amount: float, ts: int, typology: str, fraud: bool, ring_id: str | None = None
    ) -> None:
        value = round(max(0.01, amount * rng.uniform(1 - config.amount_noise, 1 + config.amount_noise)), 2)
        if typology == "structuring" and 47500 <= amount < 50000:
            value = min(49999.99, max(47500.0, value))
        transaction = Transaction(
            transaction_id=f"t{len(transactions):09d}",
            source=source,
            target=target,
            ts=ts,
            amount=value,
            kind="TRANSFER",
            fraud=fraud,
            typology=typology,
            ring_id=ring_id,
            device_id=f"d{rng.randrange(8):02d}" if rng.random() < 0.7 else None,
            ip_address=f"192.0.2.{rng.randrange(1, 30)}" if rng.random() < 0.7 else None,
        )
        transactions.append(transaction)
        if cashout_ledger is not None and target == collector and fraud:
            cashout_ledger.append(
                {
                    "transaction_id": transaction.transaction_id,
                    "source": source,
                    "target": target,
                    "ts": ts,
                    "amount": value,
                    "currency": "INR",
                    "simulation_definition": "terminal collector credit, not verified bank cash-out",
                }
            )
        tags[source].add(typology)
        tags[target].add(typology)

    for component in range(config.components):
        nodes = [new_account() for _ in range(config.accounts_per_component)]
        merchant, salary, rent, origin, hub, collector = nodes[:6]
        relays = nodes[6:-1]
        for node in nodes:
            accounts.append(Account(account_id=node, created_at=config.base_time - rng.randint(1, 365) * 86400))
        # Benign connected salary/rent/EMI and merchant flows camouflage topology.
        for index, node in enumerate(nodes):
            emit(node, nodes[(index + 1) % len(nodes)], 4000, config.base_time + index * 60, "legit_cycle", False)
        for day in range(config.days):
            base = config.base_time + day * 86400 + 3600
            for _ in range(config.noise_events_per_day):
                sender, receiver = rng.sample(nodes[:-1], 2)
                ts = base + rng.randrange(60000)
                emit(
                    sender,
                    receiver,
                    rng.lognormvariate(9, 1),
                    ts,
                    "merchant" if receiver == merchant else "ordinary",
                    False,
                )
            if day % 7 == 0:
                emit(salary, hub, 50000, base + 100, "salary", False)
                emit(hub, rent, 18000, base + 400, "rent", False)
                emit(hub, merchant, 5000, base + 600, "emi", False)
            # Legitimate pass-through/cycles are deliberately not labelled fraud.
            if day % 3 == 0:
                emit(origin, relays[0], 80000, base + 1000, "legit_relay", False)
                emit(relays[0], merchant, 76000, base + 1200, "legit_relay", False)
            if day % 4 != component % 4:
                continue
            typology = config.typologies[(component + day // 4) % len(config.typologies)]
            if typology == "dormant_activation" and day < 3:
                continue
            fraudulent = rng.random() < config.fraud_probability
            ring = f"ring-{component}"
            start = base + 7200 + rng.randint(0, config.timing_jitter_seconds)
            delay = config.delay_seconds
            amount = rng.uniform(30000, 150000)
            destination = merchant if config.merchant_hop else collector
            if typology == "fan_in":
                for i, node in enumerate(relays[:3]):
                    emit(node, hub, amount / 3, start + i * delay, typology, fraudulent, ring)
                emit(hub, destination, amount * 0.9, start + 4 * delay, typology, fraudulent, ring)
            elif typology in {"fan_out", "structuring"}:
                emit(origin, hub, amount, start, typology, fraudulent, ring)
                for i in range(config.split_count):
                    value = rng.uniform(47500, 49999) if typology == "structuring" else amount / config.split_count
                    emit(hub, relays[i % len(relays)], value, start + (i + 1) * delay, typology, fraudulent, ring)
            elif typology == "scatter_gather":
                for i, node in enumerate(relays[:3]):
                    emit(origin, node, amount / 3, start + i * delay, typology, fraudulent, ring)
                    emit(node, destination, amount * 0.3, start + (i + 4) * delay, typology, fraudulent, ring)
            elif typology == "cycle":
                cycle = [origin, hub, relays[0], origin]
                for i, (source, target) in enumerate(pairwise(cycle)):
                    emit(source, target, amount * 0.98**i, start + i * delay, typology, fraudulent, ring)
            else:
                depth = config.layering_depth if typology == "layering" else 1
                chain = [origin] + relays[:depth] + [destination]
                if typology == "dormant_activation":
                    # Relay is quiet in the preceding several days, not a class-coded feature.
                    chain = [origin, nodes[-1], destination]
                for i, (source, target) in enumerate(pairwise(chain)):
                    emit(source, target, amount * 0.96**i, start + i * delay, typology, fraudulent, ring)
                if config.merchant_hop:
                    emit(
                        merchant, collector, amount * 0.85, start + (len(chain) + 1) * delay, typology, fraudulent, ring
                    )
    return Dataset(
        source="mulenet-simulator-v1",
        seed=config.seed,
        transactions=canonical_events(transactions),
        accounts=tuple(sorted(accounts, key=lambda a: a.account_id)),
        account_typologies={key: tuple(sorted(value)) for key, value in sorted(tags.items())},
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-synthetic", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--delay-seconds", type=int, default=120)
    parser.add_argument("--split-count", type=int, default=3)
    parser.add_argument("--merchant-hop", action="store_true")
    parser.add_argument("--components", type=int, default=12)
    parser.add_argument("--accounts-per-component", type=int, default=12)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--noise-events-per-day", type=int, default=4)
    parser.add_argument("--cashout-ledger", type=Path)
    args = parser.parse_args()
    if not args.allow_synthetic:
        parser.error("Synthetic generation requires explicit --allow-synthetic")
    config = SimulationConfig(
        seed=args.seed,
        delay_seconds=args.delay_seconds,
        split_count=args.split_count,
        merchant_hop=args.merchant_hop,
        components=args.components,
        accounts_per_component=args.accounts_per_component,
        days=args.days,
        noise_events_per_day=args.noise_events_per_day,
    )
    ledger = []
    digest = write_dataset(generate(config, ledger), args.out)
    if args.cashout_ledger:
        from mulenet_core.io import canonical_json

        args.cashout_ledger.parent.mkdir(parents=True, exist_ok=True)
        args.cashout_ledger.write_bytes(
            canonical_json(
                {
                    "data_hash": digest,
                    "data_provenance": "synthetic",
                    "config": config.model_dump(mode="json"),
                    "events": ledger,
                }
            )
        )
    print(digest)


if __name__ == "__main__":
    main()
