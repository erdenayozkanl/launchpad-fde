import json, time
from dataclasses import asdict
from pathlib import Path
from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from launchpad import Evaluator, IdempotencyStore, Release, ReleaseRegistry, Telemetry

BASE = Path(__file__).parent
app = FastAPI(title="Launchpad FDE", version="0.1.0")
registry, evaluator, telemetry, idempotency = ReleaseRegistry(), Evaluator(), Telemetry(), IdempotencyStore()
registry.register(Release("stable-v1", "Answer with sources and state uncertainty.", "local-small", "active", 100))
registry.register(Release("candidate-v2", "Answer with sources, state uncertainty, and protect PII.", "local-large"))
cases = json.loads((BASE / "data" / "eval.json").read_text())

class Promote(BaseModel):
    version: str
    threshold: float = Field(default=.80, ge=0, le=1)
    canary_percent: int = Field(default=10, ge=1, le=100)
class Invoke(BaseModel):
    tenant_id: str
    message: str = Field(min_length=1, max_length=4000)

@app.get("/health")
def health(): return {"status":"ok", **telemetry.summary()}

@app.post("/releases/promote")
def promote(request: Promote):
    try:
        release = registry.releases[request.version]
        result = evaluator.score(cases, release)
        registry.promote(request.version, result["score"], request.threshold, request.canary_percent)
        return {"evaluation": result, "release": asdict(release)}
    except (KeyError, ValueError) as exc: raise HTTPException(400, str(exc))

@app.post("/releases/{version}/rollback")
def rollback(version: str):
    try: return asdict(registry.rollback(version))
    except KeyError: raise HTTPException(404, "release not found")

@app.post("/invoke")
def invoke(request: Invoke, idempotency_key: str = Header(...)):
    cached = idempotency.get(idempotency_key)
    if cached: return {**cached, "idempotent_replay": True}
    started = time.perf_counter(); release = registry.select(f"{request.tenant_id}:{idempotency_key}")
    # Adapter seam: replace with a provider call with timeout/retry/backoff.
    result = {"release": release.version, "model": release.model, "output": f"[simulated] {request.message}", "idempotent_replay": False}
    telemetry.record(ok=True, latency_ms=(time.perf_counter()-started)*1000, cost_usd=.0001, tenant=request.tenant_id, release=release.version)
    idempotency.put(idempotency_key, result)
    return result

@app.get("/metrics")
def metrics(): return telemetry.summary()
