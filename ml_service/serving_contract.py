"""Versioned internal API; model evidence is not a bank intervention instruction."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from mulenet_core.schema import Account, Epoch, Identifier, StrictModel, Transaction

ServiceEpoch = Annotated[int, Field(ge=0, json_schema_extra={"format": "int64"})]


class Snapshot(StrictModel):
    snapshot_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")] | None = None
    complete_from: ServiceEpoch
    watermark: ServiceEpoch
    events: list[Transaction] = Field(max_length=8192)
    accounts: list[Account] = Field(max_length=4096)

    @model_validator(mode="after")
    def check_clock(self):
        if self.complete_from > self.watermark:
            raise ValueError("Invalid completeness interval")
        if any(e.ts > self.watermark or e.ts < self.complete_from for e in self.events):
            raise ValueError("Event outside declared complete interval")
        if len({e.transaction_id for e in self.events}) != len(self.events):
            raise ValueError("Snapshot contains duplicate transaction IDs")
        if len({a.account_id for a in self.accounts}) != len(self.accounts):
            raise ValueError("Snapshot contains duplicate account IDs")
        if any(e.fraud is not None or e.typology or e.ring_id for e in self.events):
            raise ValueError("Training labels are forbidden in serving context")
        return self


class ScoreRequest(StrictModel):
    account_id: Identifier
    as_of: ServiceEpoch
    snapshot_id: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]
    correlation_id: Annotated[str, Field(pattern=r"^[a-zA-Z0-9-]{1,64}$")]


class ScoreResponse(StrictModel):
    account_id: str
    as_of: ServiceEpoch
    correlation_id: str
    snapshot_id: str
    model_version: str
    feature_schema_hash: str
    data_provenance: Literal["synthetic"]
    model: Literal["tabular_graph", "gnn", "fusion"]
    probability: float = Field(ge=0, le=1, allow_inf_nan=False)
    validation_threshold: float
    alert: bool
    degraded: bool
    degradation_reason: str | None
    score_components: dict[str, float | None]
    reason_codes: list[dict]
    evidence: dict
    simulated_watchlist: dict
    durations_ms: dict[str, float]
    shadow_results: list[dict] = Field(default_factory=list)
