import pytest
import datetime
import json
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from core.rules.rules_engine import RulesEngine
from core.rules.humanizer import Humanizer
from core.platforms.fiverr import FiverrPlatform
from core.platforms.upwork import UpworkPlatform
from core.platforms.freelancer import FreelancerPlatform
from core.seo.platform_seo import PlatformSEO
from core.scheduler.seo_cron import SEOScheduler
from core.skills.gig_optimizer import GigOptimizer
from core.skills.profile_optimizer import ProfileOptimizer
from core.skills.inbox_handler import InboxHandler
from core.skills.client_outreach import ClientOutreach
from core.brain.brain import BrainManager
from core.mcp.server import FPNexusMCPServer
from api.app import app

client = TestClient(app)

def test_rules_engine_banned_words_and_null_safety():
    engine = RulesEngine()
    
    # Null safety checks
    res_none = engine.audit_text(None)
    assert res_none["is_compliant"] is True
    assert len(res_none["violations"]) == 0
    
    # Empty / None text defaults to baseline readable 70.0 Flesch score
    flesch_none = engine.calculate_flesch(None)
    assert flesch_none == 70.0

    # Banned words and their inflections check
    test_text = (
        "We foster dynamic collaboration, leveraging intricate tools to facilitate seamless workflows. "
        "We harness cutting-edge tech to empower teams, underscoring our commitment to elevate solutions."
    )
    res = engine.audit_text(test_text)
    assert res["is_compliant"] is False
    found = res["banned_words_found"]
    for w in ["foster", "dynamic", "leveraging", "intricate", "facilitate", "seamless", "harness", "empower", "underscoring", "elevate"]:
        assert any(w in fw for fw in found), f"Expected violation for '{w}'"

def test_humanizer_full_replacement_map_coverage():
    humanizer = Humanizer()
    
    # Null safety
    assert humanizer.extract_clean_candidate(None) == ""
    cleaned_none, audit_none = humanizer.humanize_text(None)
    assert cleaned_none == ""
    assert audit_none["score"] == 100

    # Replacement coverage for words added in Round 4
    sample_text = (
        "This is an invaluable and intricate feature. Our dynamic and vibrant platform has an enduring, "
        "remarkable, and exceptional record. It is a sophisticated and versatile tool with noteworthy, "
        "compelling results. A true testament to our realm and ecosystem with fine interplay. "
        "We empower developers and underscore quality to garner trust with a holistic view."
    )
    cleaned, _ = humanizer.humanize_text(sample_text)
    assert "invaluable" not in cleaned.lower()
    assert "intricate" not in cleaned.lower()
    assert "dynamic" not in cleaned.lower()
    assert "vibrant" not in cleaned.lower()
    assert "testament" not in cleaned.lower()
    assert "ecosystem" not in cleaned.lower()
    assert "empower" not in cleaned.lower()
    assert "underscore" not in cleaned.lower()
    assert "garner" not in cleaned.lower()
    assert "holistic" not in cleaned.lower()

def test_fiverr_platform_edge_cases():
    fiverr = FiverrPlatform()
    
    # None fields safety
    valid, errs = fiverr.validate_gig({"title": None, "description": None, "search_tags": None})
    assert valid is False
    assert any("title is required" in e.lower() for e in errs)

    # Title ending with period '.' restriction
    valid_period, errs_period = fiverr.validate_gig({
        "title": "I will build high performance FastAPI microservices.",
        "description": "A" * 150,
        "search_tags": ["python", "fastapi", "backend", "api", "docker"]
    })
    assert valid_period is False
    assert any("cannot end with a period" in e for e in errs_period)

    # Pricing string with currency symbol parsing
    valid_price, errs_price = fiverr.validate_gig({
        "title": "I will build high performance FastAPI microservices",
        "description": "A" * 150,
        "search_tags": ["python", "fastapi", "backend", "api", "docker"],
        "pricing_tiers": {
            "basic": {"name": "Basic", "price": "$50.00", "delivery_days": 3, "description": "Desc"}
        }
    })
    assert valid_price is True

    # Delivery days boundary check (1 to 30 days) in nested pricing_tiers
    valid_days, errs_days = fiverr.validate_gig({
        "title": "I will build high performance FastAPI microservices",
        "description": "A" * 150,
        "search_tags": ["python", "fastapi", "backend", "api", "docker"],
        "pricing_tiers": {
            "basic": {"name": "Basic", "price": 50, "delivery_days": 35, "description": "Desc"}
        }
    })
    assert valid_days is False
    assert any("cannot exceed 30" in e for e in errs_days)

    # Non-string search tags formatting in markdown
    md = fiverr.format_gig_markdown({
        "title": "I will build APIs",
        "description": "Desc",
        "search_tags": [123, None, "python"]
    })
    assert "123, None, python" in md

def test_upwork_and_freelancer_platform_edge_cases():
    upwork = UpworkPlatform()
    valid, errs = upwork.validate_gig({"title": None, "description": None})
    assert valid is False
    assert any("title is required" in e.lower() for e in errs)

    freelancer = FreelancerPlatform()
    valid_f, errs_f = freelancer.validate_gig({
        "title": "A" * 105, # Max 100
        "description": "Short",
        "skills": []
    })
    assert valid_f is False
    assert any("100 characters" in e for e in errs_f)

def test_seo_null_safety_and_string_tags():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "Primary: python\nSecondary: api, backend"
    seo = PlatformSEO(mock_llm)

    # Null gig_data fields
    audit = seo.audit_gig_seo(gig_data={"title": None, "description": None, "search_tags": None})
    assert "seo_score" in audit
    assert audit["seo_score"] >= 0

    # Comma-separated string current_tags in weekly refresh
    refresh = seo.weekly_keyword_refresh(current_tags="python, scraping, api", gig_title="FastAPI Scraper", gig_category="Programming & Tech")
    assert "previous_tags" in refresh
    assert "recommended_tags" in refresh
    assert isinstance(refresh["recommended_tags"], list)

def test_seo_cron_iso_timestamp_parsing():
    mock_seo = MagicMock()
    scheduler = SEOScheduler(mock_seo)

    # Test ISO timestamp with +00:00 and with Z
    now = datetime.datetime.now(datetime.timezone.utc)
    ts_plus = (now - datetime.timedelta(days=2)).isoformat() # 2 days ago (not due)
    ts_z = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Due check with 7-day interval
    assert scheduler.is_audit_due(ts_plus, interval_days=7) is False
    assert scheduler.is_audit_due(ts_z, interval_days=7) is False
    
    # 10 days ago (due)
    ts_old = (now - datetime.timedelta(days=10)).isoformat()
    assert scheduler.is_audit_due(ts_old, interval_days=7) is True

    # Test parse_tags helper
    assert scheduler.parse_tags(None) == []
    assert scheduler.parse_tags('["python", "api"]') == ["python", "api"]
    assert scheduler.parse_tags('python, api, fastapi') == ["python", "api", "fastapi"]

def test_skills_input_normalization():
    mock_llm = MagicMock()
    mock_brain = MagicMock()
    mock_brain.get_receipts.return_value = []
    mock_brain.format_receipts_for_prompt.return_value = "No receipts."
    mock_llm.generate.return_value = json.dumps({
        "title": "I will develop high performance FastAPI microservices",
        "description": "We build fast, asynchronous APIs using FastAPI, Docker, and Redis.",
        "search_tags": ["fastapi", "api", "python", "docker", "microservice"]
    })

    # ProfileOptimizer with string core_skills
    prof_opt = ProfileOptimizer(mock_llm, mock_brain)
    res_prof = prof_opt.optimize_profile(
        primary_role="Backend Engineer",
        core_skills="Python, FastAPI, Docker, PostgreSQL",
        years_experience=5,
        platform_name="fiverr"
    )
    assert res_prof["platform"] == "fiverr"
    assert "Python" in res_prof["recommended_skills"]
    assert "FastAPI" in res_prof["recommended_skills"]

    # GigOptimizer with comma-separated target_keywords string
    gig_opt = GigOptimizer(mock_llm, mock_brain)
    res_gig = gig_opt.optimize_gig(
        topic="FastAPI Microservice",
        target_keywords="api, fast, python, microservice",
        platform_name="fiverr"
    )
    assert res_gig["platform"] == "fiverr"
    assert len(res_gig["target_keywords"]) == 4

    # InboxHandler with empty client message
    inbox = InboxHandler(mock_llm, mock_brain)
    reply_empty = inbox.reply_to_client(client_message="")
    assert any(k in reply_empty["reply_text"].lower() for k in ["specifications", "inquiry", "clarify", "timeline"])

def test_mcp_server_serialization_and_schema():
    server = FPNexusMCPServer()
    
    # Schema check for reply_to_client
    tools = server.get_tool_definitions()
    reply_tool = next(t for t in tools if t["name"] == "reply_to_client")
    assert "freelancer_rate" in reply_tool["inputSchema"]["properties"]

    # Test request with datetime serialization safety
    res = server.handle_request({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "get_freelance_receipts",
            "arguments": {"query": "api"}
        }
    })
    assert res is not None
    assert "result" in res
    assert "content" in res["result"]

def test_competitor_scan_invalid_url_raises_400():
    # Attempting to scan an invalid/unreachable URL should return 400 Bad Request
    resp = client.post("/api/competitors/scan", json={"url": "https://invalid-domain-nonexistent-12345.com/gig", "platform": "fiverr"})
    assert resp.status_code == 400
    assert "detail" in resp.json()
