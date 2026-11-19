import pytest
from launchpad import Evaluator, Release, ReleaseRegistry, Telemetry

def test_evaluation_gate_and_canary_selection():
    registry = ReleaseRegistry()
    registry.register(Release("stable", "sources uncertainty", "small", "active", 100))
    registry.register(Release("candidate", "sources uncertainty PII", "large"))
    result = Evaluator().score([{"required_terms":["sources", "PII"]}], registry.releases["candidate"])
    registry.promote("candidate", result["score"], canary_percent=10)
    assert registry.releases["candidate"].traffic_percent == 10
    assert registry.select("customer-1").status == "active"

def test_gate_blocks_weak_candidate_and_metrics():
    registry = ReleaseRegistry(); registry.register(Release("x", "no guardrails", "small"))
    with pytest.raises(ValueError): registry.promote("x", .5)
    metrics = Telemetry(); metrics.record(ok=True, latency_ms=10, cost_usd=.1); metrics.record(ok=False, latency_ms=30, cost_usd=.2)
    assert metrics.summary()["p95_ms"] == 30 and metrics.summary()["error_rate"] == .5
