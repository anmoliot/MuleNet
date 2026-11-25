"""Immutable complete snapshots cached in Redis, never silently truncated."""

import hashlib

from mulenet_core.io import canonical_json
from serving_contract import Snapshot


def snapshot_digest(complete_from, watermark, events, accounts):
    return hashlib.sha256(canonical_json({"complete_from": complete_from, "watermark": watermark,
                                        "events": [e.model_dump(mode="json") for e in sorted(events, key=lambda e: e.transaction_id)],
                                        "accounts": [a.model_dump(mode="json") for a in sorted(accounts, key=lambda a: a.account_id)]})).hexdigest()


class SnapshotCache:
    def __init__(self, redis_client, ttl=300):
        self.redis = redis_client
        self.ttl = ttl

    @staticmethod
    def key(tenant, snapshot_id):
        namespace = hashlib.sha256(tenant.encode()).hexdigest()
        return f"mulenet:snapshot:{namespace}:{snapshot_id}"

    def put(self, tenant, snapshot):
        expected = snapshot_digest(snapshot.complete_from, snapshot.watermark, snapshot.events, snapshot.accounts)
        if snapshot.snapshot_id is not None and expected != snapshot.snapshot_id:
            raise ValueError("Snapshot content hash mismatch")
        # NX makes a content-addressed value immutable; expiry is independent of ledger retention.
        self.redis.set(self.key(tenant, expected), snapshot.model_copy(update={"snapshot_id": expected}).model_dump_json(), ex=self.ttl, nx=True)
        return expected

    def get(self, tenant, snapshot_id):
        payload = self.redis.get(self.key(tenant, snapshot_id))
        if payload is None:
            raise LookupError("Snapshot cache miss; backfill the complete authoritative DB snapshot")
        snapshot = Snapshot.model_validate_json(payload)
        if snapshot_digest(snapshot.complete_from, snapshot.watermark, snapshot.events, snapshot.accounts) != snapshot_id:
            raise ValueError("Corrupt cached snapshot")
        return snapshot
