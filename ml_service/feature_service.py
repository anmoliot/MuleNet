"""Feature-only migration API; never imports unsafe legacy model loaders."""

import os
import secrets

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import Field

from mulenet_core.features import OnlineFeatureStore
from mulenet_core.schema import Account, Epoch, FeatureConfig, Identifier, StrictModel, Transaction, feature_schema_hash


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
    service_token = os.environ.get("MULENET_FEATURE_SERVICE_TOKEN", "")
    if len(service_token) < 32:
        raise RuntimeError("Set a unique MULENET_FEATURE_SERVICE_TOKEN of at least 32 characters")
    app = FastAPI(title="MuleNet as-of feature migration API")
    bearer = HTTPBearer(auto_error=False)

    def authorize(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
        if credentials is None or not secrets.compare_digest(credentials.credentials, service_token):
            raise HTTPException(401, "Invalid service credential")

    @app.post("/features", dependencies=[Depends(authorize)])
    def features(request: FeatureRequest) -> dict:
        try:
            values = online_snapshot(request.events, request.account_id, request.as_of, request.config, tuple(request.accounts))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"feature_schema_hash": feature_schema_hash(request.config), "features": values}

    return app
