"""Batch materialization uses exactly the online feature contract."""

from mulenet_core.labels import Example, materialize
from mulenet_core.schema import Dataset, FeatureConfig


def build_examples(dataset: Dataset, points: list[tuple[str, int]], horizon: int, complete_through: int, config: FeatureConfig = FeatureConfig()) -> list[Example]:
    return materialize(dataset.transactions, points, horizon, complete_through, config, dataset.accounts)
