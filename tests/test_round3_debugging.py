import pytest
from fastapi.testclient import TestClient
from api.app import app

from core.seo.platform_seo import PlatformSEO
from core.platforms.factory import PlatformFactory
from core.mcp.server import FPNexusMCPServer
from core.reach.reader import ReachReader
from unittest.mock import patch, MagicMock

client = TestClient(app)

def test_seo_technical_keyword_boundary():
    """Verify keywords with symbols like c++, c#, .net are matched correctly."""
    seo = PlatformSEO()
    
    # 1. c++
    gig_cpp = {
        "title": "I will build high performance c++ backend services",
        "description": "Looking for c++ development? I engineer c++ microservices with high throughput.",
        "search_tags": ["c++", "backend", "systems", "cpp", "performance"],
        "category": "Programming & Tech"
    }
    audit_cpp = seo.audit_gig_seo(gig_cpp, primary_keyword="c++")
    assert audit_cpp["density_pct"] > 0, "c++ density should be > 0%"
    assert any("c++" in c["note"].lower() for c in audit_cpp["checklist"] if c["item"] == "Primary Keyword in Title")

    # 2. .net
    gig_dotnet = {
        "title": "I will develop scalable .net core rest apis",
        "description": "I build production-grade .net applications with clean architecture and tests.",
        "search_tags": [".net", "c#", "aspnet", "api", "backend"],
        "category": "Programming & Tech"
    }
    audit_dotnet = seo.audit_gig_seo(gig_dotnet, primary_keyword=".net")
    assert audit_dotnet["density_pct"] > 0, ".net density should be > 0%"

def test_api_gig_audit_and_persist():
    """Verify POST /api/gigs/{gig_id}/audit computes SEO score and persists to seo_audits table."""
    # Create gig
    save_res = client.post("/api/gigs/save", json={
        "title": "I will build python automation scripts and rest apis",
        "category": "Programming & Tech",
        "search_tags": ["python", "automation", "api", "fastapi", "scraper"],
        "description": "I will build python automation scripts for data pipelines and backends with full unit test coverage.",
        "basic_tier_name": "Basic",
        "basic_tier_price": 50.0,
        "standard_tier_name": "Standard",
        "standard_tier_price": 150.0,
        "premium_tier_name": "Premium",
        "premium_tier_price": 300.0
    })
    assert save_res.status_code == 200
    gig_id = save_res.json()["gig_id"]

    # Trigger audit
    audit_res = client.post(f"/api/gigs/{gig_id}/audit")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert "seo_score" in audit_data
    assert "checklist" in audit_data

    # Verify audit is in /api/seo/audits
    audits_res = client.get("/api/seo/audits")
    assert audits_res.status_code == 200
    audits_list = audits_res.json()["audits"]
    assert any(a["gig_id"] == gig_id for a in audits_list)

    # Cleanup
    del_res = client.delete(f"/api/gigs/{gig_id}")
    assert del_res.status_code == 200

    # Verify 404 on deleting non-existent gig
    del_404 = client.delete(f"/api/gigs/{gig_id}")
    assert del_404.status_code == 404

def test_api_outreach_endpoint():
    """Verify POST /api/proposals/outreach drafts 82-rule cold outreach."""
    with patch("core.llm.client.UniversalLLMClient.generate") as mock_gen:
        mock_gen.return_value = "Observed 3.2s query latency on your tracking dashboard. We can cut your order execution latency down using async connection pooling. Would you like to review the benchmark results?"
        res = client.post("/api/proposals/outreach", json={
            "prospect_name_or_company": "Acme Logistics",
            "prospect_problem_or_tech": "Slow PostgreSQL invoice query bottlenecks",
            "outreach_channel": "direct_message",
            "specific_observation": "Observed 3.2s query latency on your tracking dashboard"
        })
        assert res.status_code == 200
        data = res.json()
        assert "outreach_text" in data
        assert "Acme Logistics" in data["prospect"]
        assert len(data["outreach_text"]) > 20

def test_api_proposals_delete_and_404():
    """Verify proposal save, delete, and 404 error handling."""
    save_res = client.post("/api/proposals/save", json={
        "platform": "upwork",
        "job_title": "FastAPI Senior Developer Needed",
        "job_description": "We need a FastAPI developer with async pg experience.",
        "proposal_text": "I can structure your FastAPI endpoints with connection pooling and pytest coverage.",
        "client_budget": "$1,000"
    })
    assert save_res.status_code == 200
    prop_id = save_res.json()["proposal_id"]

    # Delete
    del_res = client.delete(f"/api/proposals/{prop_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted_id"] if "deleted_id" in del_res.json() else del_res.json()["proposal_id"] == prop_id

    # 404 on second delete
    del_404 = client.delete(f"/api/proposals/{prop_id}")
    assert del_404.status_code == 404

def test_api_inbox_and_competitor_delete_404():
    """Verify inbox and competitor delete endpoints return 404 on invalid IDs."""
    # Delete non-existent inbox conversation
    inbox_404 = client.delete("/api/inbox/9999999")
    assert inbox_404.status_code == 404

    # Delete non-existent competitor scan
    comp_404 = client.delete("/api/competitors/9999999")
    assert comp_404.status_code == 404

    # Delete non-existent brain receipt
    brain_404 = client.delete("/api/brain/receipts/9999999")
    assert brain_404.status_code == 404

def test_platform_factory_aliases():
    """Verify platform factory correctly maps aliases."""
    p1 = PlatformFactory.get_platform("freelancer.com")
    assert p1.platform_name == "freelancer"

    p2 = PlatformFactory.get_platform("catalog")
    assert p2.platform_name == "upwork"

    p3 = PlatformFactory.get_platform("buyer_request")
    assert p3.platform_name == "fiverr"

    p4 = PlatformFactory.get_platform("contra")
    assert p4.platform_name == "upwork"


def test_mcp_all_tools_registered():
    """Verify MCP server has all 10 tools defined and accessible."""
    server = FPNexusMCPServer()
    tools = server.get_tool_definitions()
    tool_names = [t["name"] for t in tools]
    
    expected_tools = [
        "optimize_gig",
        "draft_proposal",
        "draft_outreach",
        "optimize_profile",
        "audit_gig_seo",
        "format_portfolio_project",
        "reply_to_client",
        "scan_competitor_gig",
        "get_freelance_receipts",
        "run_biweekly_seo_audit"
    ]
    for exp in expected_tools:
        assert exp in tool_names, f"Tool {exp} should be registered in MCP server"

    # Test executing draft_outreach tool
    with patch("core.llm.client.UniversalLLMClient.generate") as mock_gen:
        mock_gen.return_value = "Hello Beta Corp, here is our plan for FastAPI migration."
        outreach_res = server.execute_tool("draft_outreach", {
            "prospect_name_or_company": "Beta Corp",
            "prospect_problem_or_tech": "FastAPI migration"
        })
        assert "outreach_text" in outreach_res

        import json
        mock_gen.return_value = json.dumps({
            "title_tagline": "Senior Python Backend Engineer",
            "bio_summary": "Architecting resilient backends with FastAPI and PostgreSQL.",
            "skills_list": ["Python", "FastAPI", "PostgreSQL"],
            "portfolio_highlight": "High throughput microservices."
        })
        prof_res = server.execute_tool("optimize_profile", {
            "primary_role": "Python Backend Engineer",
            "core_skills": ["Python", "FastAPI", "PostgreSQL"]
        })
        assert "bio_summary" in prof_res

def test_reach_reader_ssl_fallback():
    """Verify ReachReader handles network responses cleanly without crashing."""
    reader = ReachReader()
    
    with patch("requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><head><title>Top Python Dev</title></head><body><h1>Senior Freelancer</h1><p>We deliver fast web scrapers.</p></body></html>"
        mock_get.return_value = mock_resp

        res = reader.read_url("https://www.fiverr.com/test-seller")
        assert res["status"] == "success"
        assert "Senior Freelancer" in res["content"]
        assert res["title"] == "Top Python Dev"
