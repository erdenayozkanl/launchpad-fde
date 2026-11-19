"""FDE-style AI deployment controls: configuration, eval gates and safe rollout."""
from __future__ import annotations

import hashlib
import math
import statistics
import time
import uuid
from dataclasses import dataclass, asdict


@dataclass
class Release:
    version: str
    prompt: str
    model: str
    status: str = "candidate"  # candidate | active | rolled_back
    traffic_percent: int = 0


class ReleaseRegistry:
    def __init__(self): self.releases: dict[str, Release] = {}

    def register(self, release: Release) -> Release:
        if release.version in self.releases: raise ValueError("version already exists")
        self.releases[release.version] = release
        return release

    def promote(self, version: str, score: float, threshold: float = .80, canary_percent: int = 10) -> Release:
        if score < threshold: raise ValueError(f"evaluation score {score:.2f} is below promotion threshold {threshold:.2f}")
        release = self.releases[version]
        if release.status != "candidate": raise ValueError("only candidate releases can be promoted")
        release.status, release.traffic_percent = "active", canary_percent
        return release

    def rollback(self, version: str) -> Release:
        release = self.releases[version]
        release.status, release.traffic_percent = "rolled_back", 0
        return release

    def select(self, request_key: str) -> Release:
        active = [r for r in self.releases.values() if r.status == "active"]
        if not active: raise RuntimeError("no active release")
        # Stable bucketing avoids a user switching versions between requests.
        bucket = int(hashlib.sha256(request_key.encode()).hexdigest()[:8], 16) % 100
        canaries = [r for r in active if 0 < r.traffic_percent < 100]
        if canaries and bucket < canaries[0].traffic_percent: return canaries[0]
        stable = next((r for r in active if r.traffic_percent == 100), None)
        return stable or active[0]


class Evaluator:
    """Small deterministic gate; replace with golden-set/LLM judge in production."""
    def score(self, cases: list[dict], candidate: Release) -> dict:
        passed = sum(all(term.casefold() in candidate.prompt.casefold() for term in case["required_terms"]) for case in cases)
        total = max(len(cases), 1)
        return {"score": passed / total, "passed": passed, "total": len(cases), "release": candidate.version}


class Telemetry:
    def __init__(self): self.events: list[dict] = []
    def record(self, **event): self.events.append({"trace_id": str(uuid.uuid4()), "at": time.time(), **event})
    def summary(self):
        values = sorted(e["latency_ms"] for e in self.events)
        def percentile(p): return values[min(len(values)-1, math.ceil(len(values) * p) - 1)] if values else 0
        return {"requests": len(values), "p50_ms": percentile(.50), "p95_ms": percentile(.95),
                "error_rate": sum(not e["ok"] for e in self.events) / max(len(values), 1),
                "estimated_cost_usd": round(sum(e.get("cost_usd", 0) for e in self.events), 6)}


class IdempotencyStore:
    def __init__(self): self.responses: dict[str, dict] = {}
    def get(self, key): return self.responses.get(key)
    def put(self, key, value): self.responses[key] = value
