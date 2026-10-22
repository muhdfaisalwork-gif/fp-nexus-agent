import pytest
import json
import os
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.app import app
from core.platforms.browser_agent import FreelanceBrowserAgent
from core.reach.feed_engine import ReachFeedEngine
from core.db.database import get_connection

client = TestClient(app)

def test_browser_agent_initialization():
    """Verify FreelanceBrowserAgent initializes and provides auth status."""
    agent = FreelanceBrowserAgent()
    status = agent.get_auth_status()
    assert "fiverr_connected" in status
    assert "upwork_connected" in status
    assert "playwright_ready" in status

def test_browser_agent_parse_cookie_input_formats():
    """Verify parse_cookie_input correctly parses all 7 cookie formats without corrupting base64 tokens."""
    agent = FreelanceBrowserAgent()

    # 1. Raw Ruby Marshal Base64 token with '==' padding
    fiverr_raw = "BAh7SUkiD3VzZXJfaWQGOgETaQMA=="
    p1 = agent.parse_cookie_input(fiverr_raw, platform="fiverr")
    assert p1["name"] == "_fiverr_session"
    assert p1["value"] == fiverr_raw

    # 2. Key=Value format
    p2 = agent.parse_cookie_input(f"_fiverr_session={fiverr_raw}", platform="fiverr")
    assert p2["name"] == "_fiverr_session"
    assert p2["value"] == fiverr_raw

    # 3. Full 'Cookie:' HTTP header
    header_input = f"Cookie: path=/; _fiverr_session={fiverr_raw}; domain=.fiverr.com; secure"
    p3 = agent.parse_cookie_input(header_input, platform="fiverr")
    assert p3["name"] == "_fiverr_session"
    assert p3["value"] == fiverr_raw

    # 4. Semicolon-delimited cookies string
    semi_input = f"guest_id=12345; _fiverr_session={fiverr_raw}; logged_in=true"
    p4 = agent.parse_cookie_input(semi_input, platform="fiverr")
    assert p4["name"] == "_fiverr_session"
    assert p4["value"] == fiverr_raw

    # 5. JSON array from browser extension export (EditThisCookie, Cookie-Editor)
    json_array = json.dumps([
        {"name": "some_cookie", "value": "123"},
        {"name": "_fiverr_session", "value": fiverr_raw}
    ])
    p5 = agent.parse_cookie_input(json_array, platform="fiverr")
    assert p5["name"] == "_fiverr_session"
    assert p5["value"] == fiverr_raw

    # 6. JSON dictionary object
    json_dict = json.dumps({"_fiverr_session": fiverr_raw})
    p6 = agent.parse_cookie_input(json_dict, platform="fiverr")
    assert p6["name"] == "_fiverr_session"
    assert p6["value"] == fiverr_raw

    # 7. Upwork JWT token
    upwork_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    p7_named = agent.parse_cookie_input(f"oauth2_global_js_token={upwork_jwt}", platform="upwork")
    assert p7_named["name"] == "oauth2_global_js_token"
    assert p7_named["value"] == upwork_jwt

    p7_raw = agent.parse_cookie_input(upwork_jwt, platform="upwork")
    assert p7_raw["name"] == "oauth2_global_js_token"
    assert p7_raw["value"] == upwork_jwt

def test_browser_agent_cookie_lifecycle_and_sqlite_sync():
    """Verify save_cookie and disconnect work cleanly and sync to SQLite database settings."""
    agent = FreelanceBrowserAgent()
    token = "BAh7SUkiD3VzZXJfaWQGOgETaQMA=="

    # Save cookie
    save_res = agent.save_cookie(token, platform="fiverr")
    assert save_res["status"] == "success"
    assert agent.is_authenticated("fiverr") is True

    # Verify SQLite database table settings updated to 'true'
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", ("FIVERR_CONNECTED",))
    row = c.fetchone()
    conn.close()
    assert row is not None
    assert row["value"] == "true"

    # Disconnect
    dc_res = agent.disconnect(platform="fiverr")
    assert dc_res["status"] == "success"
    assert agent.is_authenticated("fiverr") is False

    # Verify SQLite database table settings updated to 'false'
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", ("FIVERR_CONNECTED",))
    row = c.fetchone()
    conn.close()
    assert row is not None
    assert row["value"] == "false"

def test_reach_status_api():
    """Verify GET /api/reach/status returns proper JSON structure."""
    resp = client.get("/api/reach/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "fiverr_connected" in data
    assert "upwork_connected" in data
    assert "playwright_ready" in data

def test_reach_connect_cookie_api():
    """Verify POST /api/reach/connect-cookie connects account and updates status."""
    token = "BAh7SUkiD3VzZXJfaWQGOgETaQMA=="
    resp = client.post("/api/reach/connect-cookie", json={
        "cookie": token,
        "platform": "fiverr"
    })
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Status reflects connection
    status_resp = client.get("/api/reach/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["fiverr_connected"] is True

    # Cleanup with disconnect
    dc_resp = client.post("/api/reach/disconnect", json={"platform": "fiverr"})
    assert dc_resp.status_code == 200
    assert dc_resp.json()["status"] == "success"

def test_reach_open_system_browser_api():
    """Verify POST /api/reach/open-system-browser succeeds without opening desktop window during test."""
    with patch("webbrowser.open") as mock_open:
        mock_open.return_value = True
        resp = client.post("/api/reach/open-system-browser", json={"platform": "fiverr"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "Fiverr" in data["message"]
        mock_open.assert_called_once()

def test_reach_connect_browser_api():
    """Verify POST /api/reach/connect-browser delegates to browser agent safely."""
    with patch.object(FreelanceBrowserAgent, "launch_interactive_login") as mock_launch:
        mock_launch.return_value = {"status": "fallback_needed", "message": "Automated window fallback triggered"}
        resp = client.post("/api/reach/connect-browser", json={"platform": "fiverr"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "fallback_needed"

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
    """Verify ReachFeedEngine synthesizes winning angles grounded in the Brain without external LLM latency."""
    engine = ReachFeedEngine()
    mock_json = json.dumps({
        "executive_summary": "The client wants a robust anti-bot scraper.",
        "buyer_pain_point": "IP bans and throttling by Cloudflare.",
        "brain_proof_citation": "Verified 99.8% extraction reliability on 500k pages.",
        "recommended_hook": "Saw your need for anti-bot scraping—here is the exact proxy rotation architecture.",
        "winning_angle": "Show live benchmarks and Dockerized Playwright service."
    })
    with patch.object(engine.llm, "generate", return_value=mock_json):
        angle = engine.generate_brain_angle(
            title="Senior Python Web Scraper Developer",
            content="Looking for an expert to scrape e-commerce pricing data with anti-bot bypass.",
            platform="fiverr"
        )
        assert angle["executive_summary"] == "The client wants a robust anti-bot scraper."
        assert angle["buyer_pain_point"] == "IP bans and throttling by Cloudflare."
        assert "99.8%" in angle["brain_proof_citation"]
        assert "recommended_hook" in angle

def test_browser_agent_clean_locks(tmp_path):
    """Verify _clean_profile_locks removes stale lock files."""
    agent = FreelanceBrowserAgent()
    test_dir = str(tmp_path / "test_locks")
    os.makedirs(test_dir, exist_ok=True)
    lock_file = os.path.join(test_dir, "lockfile")
    with open(lock_file, "w") as f:
        f.write("test_pid")
    assert os.path.exists(lock_file)
    agent._clean_profile_locks(test_dir)
    assert not os.path.exists(lock_file)
