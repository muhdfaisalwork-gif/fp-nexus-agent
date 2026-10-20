import pytest
from core.db.database import init_db
from core.brain.brain import BrainManager

def test_story_bank_queries():
    init_db()
    brain = BrainManager()
    receipts = brain.get_receipts()
    assert len(receipts) >= 1

    # Query specific category
    backend_receipts = brain.get_receipts(query="latency")
    assert any("latency" in r["verified_metrics"].lower() or "latency" in r["problem"].lower() for r in backend_receipts)

def test_add_receipt():
    init_db()
    brain = BrainManager()
    new_id = brain.add_receipt(
        category="Test Category",
        title="Test Microservice Benchmark",
        client_niche="Fintech",
        problem="High response time",
        solution_stack="FastAPI, Redis",
        verified_metrics="Cut response time from 1000ms to 200ms",
        duration_days=5,
        deliverables="API endpoints"
    )
    assert new_id is not None
    assert new_id > 0
