"""Feature-only migration API; never imports unsafe legacy model loaders."""

import os

from fastapi import Depends, FastAPI, HTTPException
from pydantic import Field

from mulenet_core.features import OnlineFeatureStore
from mulenet_core.schema import Account, Epoch, FeatureConfig, Identifier, StrictModel, Transaction, feature_schema_hash
from internal_auth import service_authorizer


class FeatureRequest(StrictModel):
    events: list[Transaction] = Field(max_length=2048)
    accounts: list[Account] = Field(default_factory=list, max_length=2048)
    account_id: Identifier
    as_of: Epoch
    config: FeatureConfig = FeatureConfig()


def online_snapshot(events: list[Transaction], account_id: str, as_of: int, config: FeatureConfig = FeatureConfig(), accounts: tuple[Account, ...] = ()) -> dict[str, float]:
    store = OnlineFeatureStore(config, accounts)
    for event in events:
        store.ingest(event)
    return store.snapshot(account_id, as_of)


def create_app() -> FastAPI:
    """Run with uvicorn feature_service:create_app --factory --host 127.0.0.1."""
    require = service_authorizer(os.environ.get("MULENET_SERVICE_SECRET", ""))
    app = FastAPI(title="MuleNet as-of feature migration API")
    @app.post("/features", dependencies=[Depends(require("features"))])
    def features(request: FeatureRequest) -> dict:
        try:
            values = online_snapshot(request.events, request.account_id, request.as_of, request.config, tuple(request.accounts))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"feature_schema_hash": feature_schema_hash(request.config), "features": values}

    return app
