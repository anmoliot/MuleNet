"""Validated, identifier-free training reference for distribution monitoring."""

from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, model_validator

from .schema import FeatureConfig, StrictModel, feature_names, feature_schema_hash

Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Finite = Annotated[float, Field(allow_inf_nan=False)]
ModelPath = Literal["tabular_graph", "gnn", "fusion"]


class DriftReference(StrictModel):
    format_version: Literal[1] = 1
    feature_schema_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    feature_names: tuple[str, ...]
    source_split: Literal["TRAIN"]
    data_provenance: Literal["synthetic"]
    selection: Literal["seeded uniform sample without replacement"]
    seed: int
    train_rows: int = Field(ge=2)
    features: tuple[tuple[Finite, ...], ...] = Field(min_length=2, max_length=2048)
    scores: dict[ModelPath, tuple[Probability, ...]]

    @model_validator(mode="after")
    def aligned(self) -> "DriftReference":
        if not self.feature_names or len(set(self.feature_names)) != len(self.feature_names):
            raise ValueError("Drift reference requires unique feature names")
        if len(self.features) > self.train_rows or any(len(row) != len(self.feature_names) for row in self.features):
            raise ValueError("Drift reference rows or dimensions are invalid")
        if set(self.scores) != {"tabular_graph", "gnn", "fusion"} or any(
            len(values) != len(self.features) for values in self.scores.values()
        ):
            raise ValueError("Drift scores do not match the reference sample")
        return self


def load_reference(directory: Path, config: FeatureConfig) -> DriftReference:
    path = directory / "drift-reference.json"
    if path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("Drift reference exceeds the artifact budget")
    reference = DriftReference.model_validate_json(path.read_bytes())
    if reference.feature_schema_hash != feature_schema_hash(config) or reference.feature_names != feature_names(config):
        raise ValueError("Drift reference feature schema mismatch")
    return reference
