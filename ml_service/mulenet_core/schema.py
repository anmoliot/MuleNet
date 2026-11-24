"""Canonical event-time contracts; labels never enter the feature vector."""

from __future__ import annotations

import hashlib
import json
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Identifier = Annotated[str, Field(min_length=1, max_length=256)]
Epoch = Annotated[int, Field(ge=0)]
Money = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class Transaction(StrictModel):
    transaction_id: Identifier
    source: Identifier
    target: Identifier
    ts: Epoch
    amount: Money
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] = "INR"
    kind: Identifier = "TRANSFER"
    device_id: Identifier | None = None
    ip_address: Identifier | None = None
    fraud: bool | None = None
    typology: Identifier | None = None
    ring_id: Identifier | None = None
    sender_balance_before: Money | None = None
    sender_balance_after: Money | None = None
    receiver_balance_before: Money | None = None
    receiver_balance_after: Money | None = None


class Account(StrictModel):
    account_id: Identifier
    created_at: Epoch


class FeatureConfig(StrictModel):
    windows: tuple[int, ...] = Field(default=(3600, 86400, 604800), strict=False)
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")] = "INR"
    history_seconds: Annotated[int, Field(gt=604800)] = 5184000
    structuring_threshold: Annotated[float, Field(gt=0, allow_inf_nan=False)] = 50000.0
    max_graph_nodes: Annotated[int, Field(ge=2, le=100000)] = 4096
    max_graph_edges: Annotated[int, Field(ge=1, le=1000000)] = 100000
    max_cycles: Annotated[int, Field(ge=1, le=100000)] = 10000

    @model_validator(mode="after")
    def validate_windows(self) -> FeatureConfig:
        if not self.windows or tuple(sorted(set(self.windows))) != self.windows:
            raise ValueError("windows must be unique, positive and increasing")
        if any(w <= 0 or w >= self.history_seconds for w in self.windows):
            raise ValueError("each window must be positive and shorter than history")
        return self


WINDOW_FEATURES = (
    "in_degree", "out_degree", "log_recv", "log_sent", "unique_in", "unique_out",
    "counterparty_entropy", "pass_through_ratio", "dwell_seconds", "dwell_observed",
    "velocity_zscore", "new_payee_ratio", "burstiness", "round_amount_ratio",
    "structuring_score", "device_sharing_degree", "ip_sharing_degree",
    "device_observed", "ip_observed", "in_flow_hop1", "in_flow_hop2", "in_flow_hop3",
    "out_flow_hop1", "out_flow_hop2", "out_flow_hop3", "cycle_count", "clustering",
    "pagerank", "fan_in_ratio", "fan_out_ratio", "balance_delta_error",
    "balance_delta_observed",
)


def feature_names(config: FeatureConfig = FeatureConfig()) -> tuple[str, ...]:
    return ("account_age_seconds", "account_age_known") + tuple(
        f"{name}_{window}s" for window in config.windows for name in WINDOW_FEATURES
    )


def feature_schema_hash(config: FeatureConfig = FeatureConfig()) -> str:
    payload = {
        "definition": "asof-v1-left-open-right-closed-fifo-dwell-hop-bfs",
        "config": config.model_dump(mode="json"),
        "features": feature_names(config),
        "event_schema": Transaction.model_json_schema(),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Dataset(StrictModel):
    data_provenance: Literal["synthetic"] = "synthetic"
    source: Identifier
    seed: int | None = None
    transactions: tuple[Transaction, ...]
    accounts: tuple[Account, ...] = ()
    account_typologies: dict[str, tuple[str, ...]] = Field(default_factory=dict)
