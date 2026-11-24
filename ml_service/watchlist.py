"""Explicit simulation adapter; no I4C/NCRP or other agency connectivity."""

from typing import Protocol


class WatchlistProvider(Protocol):
    def lookup(self, tenant: str, account_id: str) -> dict: ...


class SimulatedI4CProvider:
    def __init__(self, entries=()):
        self.entries = frozenset(entries)

    def lookup(self, tenant, account_id):
        return {"provider": "SimulatedI4CProvider", "simulated": True,
                "matched": (tenant, account_id) in self.entries,
                "authority": "none", "probability_uplift": None}
