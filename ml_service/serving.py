"""Internal, strict, artifact-backed candidate service. No automatic training."""

import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

import networkx as nx
import redis
from adjacency_cache import SnapshotCache
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from gnn_deadline import GnnDeadline
from internal_auth import service_authorizer
from live_drift import LiveDrift
from mulenet_core.calibration import calibrated_probabilities
from mulenet_core.features import extract_features
from mulenet_core.labels import Example
from mulenet_core.models import ModelBundle
from mulenet_core.schema import feature_schema_hash
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from serving_contract import ScoreRequest, ScoreResponse, Snapshot
from starlette.concurrency import run_in_threadpool
from training.train_gnn import snapshot_graph
from watchlist import SimulatedI4CProvider


def create_app(*, bundle=None, cache=None, secret=None, gnn=None):
    secret = secret or os.environ.get("MULENET_SERVICE_SECRET", "")
    require = service_authorizer(secret)
    score_authorization = Depends(require("score"))
    cache_authorization = Depends(require("cache"))
    registry_models = None
    if bundle is None and os.environ.get("MULENET_REGISTRY_DIR") and os.environ.get("MULENET_MODEL_DIR"):
        raise RuntimeError("Choose a registry or a fixed model directory, not both")
    if bundle is None and os.environ.get("MULENET_REGISTRY_DIR"):
        from model_registry import ModelRegistry

        registry_models = ModelRegistry(
            Path(os.environ["MULENET_REGISTRY_DIR"]),
            allow_synthetic=os.environ.get("MULENET_ALLOW_SYNTHETIC") == "true",
        )
        bundle = registry_models.active
    if bundle is None:
        directory = os.environ.get("MULENET_MODEL_DIR")
        if not directory:
            raise RuntimeError("MULENET_MODEL_DIR is required; no model or synthetic fallback")
        allow_synthetic = os.environ.get("MULENET_ALLOW_SYNTHETIC") == "true"
        bundle = ModelBundle(Path(directory), allow_synthetic=allow_synthetic)
        if bundle.training["data_provenance"] == "synthetic" and not allow_synthetic:
            raise RuntimeError("Synthetic candidate serving requires explicit MULENET_ALLOW_SYNTHETIC=true")
    config = bundle.config
    if cache is None:
        url = os.environ.get("MULENET_REDIS_URL")
        if not url:
            raise RuntimeError("MULENET_REDIS_URL is required")
        client = redis.Redis.from_url(url, socket_connect_timeout=0.2, socket_timeout=0.2)
        client.ping()
        cache = SnapshotCache(client)
    selected = bundle.training.get("selected_model", bundle.training["default_deep_path"])
    if selected not in {"tabular_graph", "gnn", "fusion"}:
        raise RuntimeError("Unsupported validation-selected model")
    runner = gnn
    if selected in {"gnn", "fusion"} and runner is None:
        runner = GnnDeadline(bundle.directory / "gnn.ts")
    registry = CollectorRegistry()
    latency = Histogram("mulenet_ml_stage_seconds", "Observed synchronous stage time", ["stage"], registry=registry)
    degraded = Counter("mulenet_ml_degraded_total", "Explicit graph-tabular fallbacks", registry=registry)
    scores_count = Counter("mulenet_ml_scores_total", "Successful candidate decisions", ["model"], registry=registry)
    watchlist = SimulatedI4CProvider()
    drift = LiveDrift(registry)

    @asynccontextmanager
    async def lifespan(app):
        yield
        if runner:
            runner.close()

    app = FastAPI(
        title="MuleNet internal scoring API",
        version="1.0.0",
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.middleware("http")
    async def limits(request: Request, call_next):
        if request.headers.get("content-encoding", "identity") != "identity":
            return Response(status_code=415)
        length = request.headers.get("content-length")
        if length and (not length.isdigit() or int(length) > 2_000_000):
            return Response(status_code=413)
        if request.method in {"POST", "PUT", "PATCH"}:
            body = bytearray()
            async for chunk in request.stream():
                body.extend(chunk)
                if len(body) > 2_000_000:
                    return Response(status_code=413)
            request._body = bytes(body)
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health")
    def health():
        return {"status": "alive"}

    @app.get("/openapi.json", dependencies=[Depends(require("contract"))])
    def contract():
        return app.openapi()

    metrics_authorization = Depends(require("metrics"))

    @app.get(
        "/metrics",
        response_class=Response,
        responses={200: {"content": {"text/plain": {"schema": {"type": "string"}}}}},
    )
    def metrics(claims=metrics_authorization):
        return Response(
            generate_latest(registry) + drift.metrics(claims["tenant"]), media_type="text/plain; version=0.0.4"
        )

    @app.get("/v1/drift", operation_id="tenantDrift")
    def tenant_drift(claims=metrics_authorization):
        return {"windows": drift.snapshot(claims["tenant"]), "automatic_action": False}

    @app.get("/ready", dependencies=[Depends(require("score"))])
    def ready():
        return {
            "status": "ready",
            "model_version": bundle.manifest["model_version"],
            "feature_schema_hash": feature_schema_hash(config),
            "model": selected,
            "data_provenance": "synthetic",
            "production_approved": False,
        }

    @app.post("/v1/snapshots", operation_id="cacheSnapshot")
    def put_snapshot(snapshot: Snapshot, claims=cache_authorization):
        try:
            snapshot_id = cache.put(claims["tenant"], snapshot)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except redis.RedisError:
            raise HTTPException(503, "Adjacency cache unavailable") from None
        return {"snapshot_id": snapshot_id}

    def score_sync(request, snapshot, candidate, tenant):
        bundle = candidate
        selected = bundle.training.get("selected_model", bundle.training["default_deep_path"])
        started = time.perf_counter()
        events = tuple(e for e in snapshot.events if e.ts <= request.as_of)
        if len({e.source for e in events} | {e.target for e in events} | {request.account_id}) > config.max_graph_nodes:
            raise ValueError("Complete context exceeds graph node cap; no silent truncation")
        if not snapshot.complete_from <= request.as_of <= snapshot.watermark:
            raise ValueError("As-of point outside complete ledger interval")
        created = {a.account_id: a for a in snapshot.accounts}
        if any(a.created_at > request.as_of for a in created.values() if a.account_id == request.account_id):
            raise ValueError("Account not created at as-of time")
        with latency.labels("feature").time():
            features = extract_features(events, request.account_id, request.as_of, config, created)
        feature_ms = (time.perf_counter() - started) * 1000
        matrix = bundle.matrix([features])
        with latency.labels("tabular").time():
            raw = bundle.graph_tabular.predict_proba(matrix)[:, 1]
            graph_score = float(calibrated_probabilities(bundle.calibration["tabular_graph"], raw)[0])
            tabular_raw = bundle.tabular.predict_proba(matrix[:, bundle.training["tabular_indices"]])[:, 1]
            tabular_score = float(calibrated_probabilities(bundle.calibration["tabular"], tabular_raw)[0])
            anomaly_signal = float(-bundle.anomaly.score_samples(matrix)[0])
        score, model, reason = graph_score, "tabular_graph", None
        gnn_score = None
        if selected in {"gnn", "fusion"}:
            try:
                row = Example(request.account_id, request.as_of, request.as_of, 0, features, (), ())
                graph = snapshot_graph(events, [row], config, snapshot.accounts)
                # Bound the inference ego graph after computing features on the complete context.
                from torch_geometric.utils import k_hop_subgraph

                index = graph.account_ids.index(request.account_id)
                nodes, edges, mapping, mask = k_hop_subgraph(index, 3, graph.edge_index, relabel_nodes=True)
                graph.x = graph.x[nodes]
                graph.edge_attr = graph.edge_attr[mask]
                graph.edge_index = edges
                with latency.labels("gnn").time():
                    values = runner.predict(graph)
                raw_gnn = float(values[int(mapping[0])])
                gnn_score = float(calibrated_probabilities(bundle.calibration["gnn"], [raw_gnn])[0])
                score = float(bundle.predict([features], [raw_gnn])[selected][0])
                model = selected
            except (TimeoutError, RuntimeError) as exc:
                reason = str(exc)
                degraded.inc()
        threshold = bundle.training["thresholds"][model]
        top = bundle.explain_tabular(features)
        evidence_graph = nx.DiGraph()
        past = [e for e in events if request.as_of - max(config.windows) < e.ts]
        evidence_graph.add_edges_from((e.source, e.target) for e in past)
        neighbors = (
            nx.single_source_shortest_path_length(evidence_graph.to_undirected(), request.account_id, cutoff=3)
            if request.account_id in evidence_graph
            else {request.account_id: 0}
        )
        evidence_edges = [
            {
                "transaction_id": e.transaction_id,
                "source": e.source,
                "target": e.target,
                "ts": e.ts,
                "amount": e.amount,
                "currency": e.currency,
            }
            for e in past
            if e.source in neighbors and e.target in neighbors
        ]
        drift.observe(tenant, bundle, features, score, model)
        return {
            "account_id": request.account_id,
            "as_of": request.as_of,
            "correlation_id": request.correlation_id,
            "snapshot_id": request.snapshot_id,
            "model_version": bundle.manifest["model_version"],
            "feature_schema_hash": feature_schema_hash(config),
            "data_provenance": "synthetic",
            "model": model,
            "probability": score,
            "validation_threshold": threshold,
            "alert": bool(score >= threshold),
            "degraded": reason is not None,
            "degradation_reason": reason,
            "score_components": {
                "tabular": tabular_score,
                "tabular_graph": graph_score,
                "gnn": gnn_score,
                "anomaly_signal": anomaly_signal,
                "watchlist_uplift": None,
            },
            "reason_codes": [
                {"code": "TABULAR_SHAP", "model": "tabular_graph", "features": top},
                {
                    "code": "FORECAST_SCOPE",
                    "label_horizon_seconds": bundle.training.get("label_horizon_seconds", 21600),
                },
            ],
            "evidence": {
                "edges": evidence_edges[:200],
                "truncated_for_display": len(evidence_edges) > 200,
                "total_edges": len(evidence_edges),
                "contribution": "observed context, not causal GNN explanation",
            },
            "simulated_watchlist": watchlist.lookup(tenant, request.account_id),
            "durations_ms": {"feature": feature_ms, "total": (time.perf_counter() - started) * 1000},
            "shadow_results": registry_models.shadow(features) if registry_models else [],
        }

    @app.post("/v1/score", response_model=ScoreResponse, operation_id="score")
    async def score(request: ScoreRequest, claims=score_authorization):
        try:
            with latency.labels("cache").time():
                snapshot = await run_in_threadpool(cache.get, claims["tenant"], request.snapshot_id)
            candidate = registry_models.choose(claims["tenant"], request.account_id) if registry_models else bundle
            result = await run_in_threadpool(score_sync, request, snapshot, candidate, claims["tenant"])
            scores_count.labels(result["model"]).inc()
            return result
        except LookupError:
            raise HTTPException(409, "Snapshot missing; authoritative DB backfill required") from None
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except redis.RedisError:
            raise HTTPException(503, "Adjacency cache unavailable") from None

    return app
