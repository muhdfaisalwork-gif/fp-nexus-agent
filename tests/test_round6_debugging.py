import json
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from api.app import app
from core.db.database import get_connection
from core.llm.client import UniversalLLMClient
from core.platforms.fiverr import FiverrPlatform
from core.platforms.upwork import UpworkPlatform
from core.platforms.freelancer import FreelancerPlatform
from core.skills.gig_optimizer import GigOptimizer
from core.skills.proposal_writer import ProposalWriter

client = TestClient(app)


def test_platform_validate_proposal_null_safety():
    """Verify validate_proposal handles None across all platforms without AttributeError."""
    for platform_cls in (FiverrPlatform, UpworkPlatform, FreelancerPlatform):
        plat = platform_cls()
        is_valid, errors = plat.validate_proposal(None)
        assert is_valid is False
        assert len(errors) >= 1


def test_fiverr_negative_price_and_days_validation():
    """Verify negative prices and delivery days are caught by Fiverr validator and clamped by GigOptimizer."""
    fiverr = FiverrPlatform()
    gig_data = {
        "title": "I will build a high speed python fastapi microservice",
        "description": "Clean, production-ready FastAPI microservice with full test coverage.",
        "search_tags": ["python", "fastapi", "api", "backend", "docker"],
        "basic_tier_price": -25,
        "basic_tier_delivery_days": -3
    }
    is_valid, issues = fiverr.validate_gig(gig_data)
    assert is_valid is False
    assert any("less than $5" in err for err in issues)
    assert any("at least 1" in err for err in issues)

    # Verify GigOptimizer clamps negative values to minimum 5.0 and 1 instead of flipping sign to +25 and +3
    mock_llm = MagicMock(spec=UniversalLLMClient)
    mock_llm.generate.return_value = json.dumps({
        "title": "I will build a high speed python fastapi microservice",
        "description": "Clean, production-ready FastAPI microservice with full test coverage.",
        "search_tags": ["python", "fastapi", "api", "backend", "docker"],
        "basic_tier_price": "-25",
        "basic_tier_delivery_days": "-3"
    })
    opt = GigOptimizer(llm_client=mock_llm)
    res = opt.optimize_gig("FastAPI microservice", platform_name="fiverr")
    assert res["basic_tier_price"] == 5.0
    assert res["basic_tier_delivery_days"] == 1


def test_settings_api_key_masking_and_preservation():
    """Verify API keys are masked in GET /api/settings/ and not overwritten by masked placeholders."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = 'OPENROUTER_API_KEY'")
    row = c.fetchone()
    original_key = row["value"] if row else ""
    conn.close()

    try:
        test_secret = "sk-or-v1-1234567890abcdef1234567890abcdef"
        post_res = client.post("/api/settings/", json={"OPENROUTER_API_KEY": test_secret})
        assert post_res.status_code == 200

        get_res = client.get("/api/settings/")
        assert get_res.status_code == 200
        data = get_res.json()
        # Ensure full secret is NOT exposed in settings dict
        assert data["settings"]["OPENROUTER_API_KEY"] != test_secret
        assert "..." in data["settings"]["OPENROUTER_API_KEY"]
        assert data["masked_api_key"] == data["settings"]["OPENROUTER_API_KEY"]

        # Attempt to save masked key back — should be ignored and preserve real key in DB
        masked_val = data["masked_api_key"]
        client.post("/api/settings/", json={"OPENROUTER_API_KEY": masked_val})

        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT value FROM settings WHERE key = 'OPENROUTER_API_KEY'")
        saved_val = c.fetchone()["value"]
        conn.close()
        assert saved_val == test_secret
    finally:
        conn = get_connection()
        c = conn.cursor()
        c.execute(
            "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES ('OPENROUTER_API_KEY', ?, CURRENT_TIMESTAMP)",
            (original_key,)
        )
        conn.commit()
        conn.close()


def test_seo_weekly_refresh_route_string_tags():
    """Verify POST /api/seo/weekly-refresh accepts comma-separated string tags without 422."""
    resp = client.post("/api/seo/weekly-refresh", json={
        "current_tags": "python, fastapi, rest api",
        "gig_title": "I will build python rest api",
        "gig_category": "Programming & Tech"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "recommended_tags" in data
    assert len(data["recommended_tags"]) == 5


def test_health_check_endpoint():
    """Verify GET /api/health returns 200 OK for deployment monitoring."""
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["service"] == "fp-nexus-agent"


def test_proposal_writer_null_inputs():
    """Verify ProposalWriter handles None job_description and None LLM output cleanly."""
    mock_llm = MagicMock(spec=UniversalLLMClient)
    mock_llm.generate.return_value = None
    writer = ProposalWriter(llm_client=mock_llm)
    res = writer.draft_proposal(job_description=None, platform_name="upwork")
    assert "proposal_text" in res
    assert res["platform"] == "upwork"
