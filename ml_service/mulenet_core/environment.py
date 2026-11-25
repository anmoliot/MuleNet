"""Record the official XGBoost distribution variant without substituting models."""

import importlib.metadata as metadata


def package_version(name: str) -> str:
    if name != "xgboost":
        return metadata.version(name)
    distributions = metadata.packages_distributions().get("xgboost", [])
    accepted = [name for name in distributions if name.lower().replace("_", "-") in {"xgboost", "xgboost-cpu"}]
    if len(accepted) != 1:
        raise RuntimeError("Install exactly one official XGBoost distribution; no alternate-model fallback is supported")
    return metadata.version(accepted[0])
