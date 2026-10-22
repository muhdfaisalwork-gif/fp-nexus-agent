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

    # Test delete
    post_id = add_resp.json()["id"]
    del_resp = client.delete(f"/api/reach/feed/{post_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Test delete non-existent 404
    del_404 = client.delete("/api/reach/feed/99999999")
    assert del_404.status_code == 404

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

def test_open_system_browser_api():
    """Verify POST /api/reach/open-system-browser succeeds."""
    resp = client.post("/api/reach/open-system-browser", json={"platform": "fiverr"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("success", "opened_system_browser")
    assert "Fiverr" in data["message"]

def test_browser_agent_clean_locks(tmp_path):
    """Verify _clean_profile_locks removes stale lock files."""
    agent = FreelanceBrowserAgent()
    test_dir = str(tmp_path / "test_locks")
    import os
    os.makedirs(test_dir, exist_ok=True)
    lock_file = os.path.join(test_dir, "lockfile")
    with open(lock_file, "w") as f:
        f.write("test_pid")
    assert os.path.exists(lock_file)
    agent._clean_profile_locks(test_dir)
    assert not os.path.exists(lock_file)

