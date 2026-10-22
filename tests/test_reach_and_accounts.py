import pytest
from fastapi.testclient import TestClient
from api.app import app
from core.platforms.browser_agent import FreelanceBrowserAgent
from core.reach.feed_engine import ReachFeedEngine

client = TestClient(app)

def test_browser_agent_initialization():
    """Verify FreelanceBrowserAgent initializes and provides auth status."""
    agent = FreelanceBrowserAgent()
    status = agent.get_auth_status()
    assert "fiverr_connected" in status
    assert "upwork_connected" in status
    assert "playwright_ready" in status

def test_browser_agent_cookie_lifecycle():
    """Verify save_cookie and disconnect work cleanly."""
    agent = FreelanceBrowserAgent()
    # Test valid cookie save
    save_res = agent.save_cookie("test_session_token_1234567890", platform="fiverr")
    assert save_res["status"] == "success"
    assert agent.is_authenticated("fiverr") is True

    # Test disconnect
    dc_res = agent.disconnect(platform="fiverr")
    assert dc_res["status"] == "success"
    assert agent.is_authenticated("fiverr") is False

def test_reach_status_api():
    """Verify GET /api/reach/status returns proper JSON structure."""
    resp = client.get("/api/reach/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "fiverr_connected" in data
    assert "playwright_ready" in data

def test_reach_feed_lifecycle_api():
    """Verify adding to feed and fetching feed via API."""
    add_resp = client.post("/api/reach/feed", json={
        "platform": "upwork",
        "author_name": "Test Client",
        "post_text": "Need Python FastAPI backend engineer to build scalable microservices.",
        "post_url": "https://www.upwork.com/jobs/~0123456",
        "budget": "$1,500"
    })
    assert add_resp.status_code == 200
    assert add_resp.json()["status"] == "success"

    feed_resp = client.get("/api/reach/feed")
    assert feed_resp.status_code == 200
    posts = feed_resp.json().get("posts", [])
    assert len(posts) > 0
    assert any("FastAPI backend" in p.get("post_text", "") for p in posts)

def test_reach_feed_engine_brain_angle():
    """Verify ReachFeedEngine synthesizes winning angles grounded in the Brain."""
    engine = ReachFeedEngine()
    angle = engine.generate_brain_angle(
        title="Senior Python Web Scraper Developer",
        content="Looking for an expert to scrape e-commerce pricing data with anti-bot bypass and high concurrency.",
        platform="fiverr"
    )
    assert "executive_summary" in angle
    assert "buyer_pain_point" in angle
    assert "brain_proof_citation" in angle
    assert "recommended_hook" in angle
