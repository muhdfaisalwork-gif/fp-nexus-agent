import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from api.app import app
from core.llm.client import UniversalLLMClient, OpenRouterProvider
from core.skills.gig_optimizer import GigOptimizer
from core.skills.profile_optimizer import ProfileOptimizer
from core.skills.inbox_handler import InboxHandler
from core.reach.scanner import CompetitorScanner
from core.skills.client_outreach import ClientOutreach
from core.skills.project_uploader import ProjectUploader
from core.seo.platform_seo import PlatformSEO
from core.rules.humanizer import Humanizer
from core.rules.rules_engine import RulesEngine
from core.db.database import get_connection, init_db

client = TestClient(app)

def test_client_openrouter_free_model_default():
    """Verify that OpenRouter default fallback is an active free model and not an obsolete 404 slug."""
    llm = UniversalLLMClient()
    default_model = llm.get_model_for_provider("openrouter")
    assert default_model in OpenRouterProvider.FREE_MODELS
    assert "gemma-4-31b-it" not in default_model


def test_client_safe_fallback_schemas():
    """Verify that all _generate_safe_fallback responses match the exact schema expected by callers."""
    llm = UniversalLLMClient()

    # 1. Profile fallback schema
    profile_fb = llm._generate_safe_fallback("create a profile headline and bio summary")
    import json
    p_data = json.loads(profile_fb)
    assert "headline" in p_data or "title_headline" in p_data
    assert "bio_summary" in p_data or "bio_description" in p_data
    assert "recommended_skills" in p_data or "skills" in p_data

    # 2. Gig fallback schema
    gig_fb = llm._generate_safe_fallback("return json with tier packages for gig")
    g_data = json.loads(gig_fb)
    assert "basic_tier_name" in g_data
    assert "basic_tier_price" in g_data
    assert "standard_tier_name" in g_data
    assert "premium_tier_name" in g_data
    assert "faqs" in g_data
    assert isinstance(g_data["faqs"], list)
    assert "question" in g_data["faqs"][0]

    # 3. Inbox reply fallback schema
    inbox_fb = llm._generate_safe_fallback("draft a client reply for detected_intent")
    i_data = json.loads(inbox_fb)
    assert "detected_intent" in i_data
    assert "recommended_action" in i_data
    assert "reply_text" in i_data
    assert "suggested_price" in i_data
    # Rule 7 & 41: No generic opener formula
    assert not i_data["reply_text"].lower().startswith("thanks for reaching out")

    # 4. Competitor fallback schema
    comp_fb = llm._generate_safe_fallback("analyze competitor counter_strategy")
    c_data = json.loads(comp_fb)
    assert "competitor_name" in c_data
    assert "key_strengths" in c_data
    assert "buyer_pain_points_or_gaps" in c_data
    assert "counter_strategy" in c_data


def test_skills_null_raw_output_handling():
    """Verify that skills do not raise TypeError or AttributeError when LLM returns None or empty string."""
    mock_llm = MagicMock(spec=UniversalLLMClient)
    mock_llm.generate.return_value = None

    # 1. GigOptimizer with None output
    gig_opt = GigOptimizer(llm_client=mock_llm)
    gig_res = gig_opt.optimize_gig(topic="Python API Development", platform_name="fiverr")
    assert gig_res["is_valid"] is True
    assert "title" in gig_res
    assert len(gig_res["search_tags"]) == 5

    # 2. ProfileOptimizer with None output
    prof_opt = ProfileOptimizer(llm_client=mock_llm)
    prof_res = prof_opt.optimize_profile(primary_role="Backend Engineer", core_skills=["Python", "FastAPI"])
    assert "headline" in prof_res
    assert "bio_summary" in prof_res
    assert len(prof_res["recommended_skills"]) >= 2

    # 3. InboxHandler with None output
    inbox_h = InboxHandler(llm_client=mock_llm)
    inbox_res = inbox_h.reply_to_client(client_message="What is your pricing?", conversation_context="API")
    assert "reply_text" in inbox_res
    assert inbox_res["suggested_price"] > 0

    # 4. CompetitorScanner with None output
    mock_reader = MagicMock()
    mock_reader.read_url.return_value = {"status": "success", "content": "Sample Seller Page", "title": "Top Gig"}
    scanner = CompetitorScanner(reader=mock_reader, llm=mock_llm)
    scan_res = scanner.scan_competitor_url(
        url="https://fiverr.com/seller/top-gig",
        platform_name="fiverr"
    )
    assert scan_res["status"] == "success"
    assert scan_res["competitor_name"] == "Competitor Seller"

    # 5. ClientOutreach with None prospect or parameters
    outreach = ClientOutreach(llm_client=mock_llm)
    outreach_res = outreach.draft_outreach(
        prospect_name_or_company=None,
        prospect_problem_or_tech=None,
        specific_observation=None
    )
    assert outreach_res["prospect"] == "Prospective Client"
    assert "outreach_text" in outreach_res

    # 6. ProjectUploader with None parameters
    uploader = ProjectUploader(llm_client=mock_llm)
    uploader_res = uploader.format_project_case_study(
        project_title=None,
        niche_or_category=None,
        problem_solved=None,
        tech_stack=None,
        results_or_metrics=None,
        save_to_brain=False
    )
    assert uploader_res["title"] == "Client Technical Implementation"
    assert "case_study_markdown" in uploader_res


def test_platform_seo_non_string_tags_and_json_string():
    """Verify that PlatformSEO handles non-string tags and JSON string representations without crashing."""
    mock_llm = MagicMock(spec=UniversalLLMClient)
    mock_llm.generate.return_value = "python api, fastapi, rest api, backend dev, docker"
    seo = PlatformSEO(llm_client=mock_llm)

    # 1. Non-string tag elements (integers, None)
    gig_with_bad_tags = {
        "title": "I will build high performance fastapi rest backend",
        "description": "I engineer robust fastapi rest backend services with complete test suites and documentation.",
        "search_tags": [123, None, "python", "fastapi", "rest api"]
    }
    audit = seo.audit_gig_seo(gig_with_bad_tags, primary_keyword="fastapi rest backend")
    assert "seo_score" in audit
    assert audit["seo_score"] > 0

    # 2. JSON string tags format from SQLite
    gig_with_json_tags = {
        "title": "I will build high performance fastapi rest backend",
        "description": "I engineer robust fastapi rest backend services with complete test suites and documentation.",
        "search_tags": '["python", "fastapi", "rest api", "backend", "docker"]'
    }
    audit_json = seo.audit_gig_seo(gig_with_json_tags, primary_keyword="fastapi rest backend")
    # All 5 tags utilized
    tag_item = [item for item in audit_json["checklist"] if item["item"] == "Tag Count"][0]
    assert tag_item["status"] == "pass"

    # 3. Weekly keyword refresh with JSON string input
    refresh_res = seo.weekly_keyword_refresh(
        current_tags='["python", "api"]',
        gig_title="Python API Services",
        gig_category="Programming"
    )
    assert "recommended_tags" in refresh_res
    assert len(refresh_res["recommended_tags"]) == 5
    assert refresh_res["previous_tags"] == ["python", "api"]


def test_humanizer_em_dash_sync_with_rules_engine():
    """Verify Humanizer and RulesEngine have synchronized em-dash calculations."""
    text_150_words = (
        "I build reliable data pipelines and backend systems that operate without silent failures. "
        "Every endpoint includes automated tests — covering both expected paths and edge cases — to ensure long-term stability. "
        "In a recent deployment, I reduced query latency from 800ms down to 120ms by introducing connection pooling and indexed lookups. "
        "The system handled over 40,000 daily requests with zero service interruptions. "
        "You receive complete documentation, Docker compose configurations, and clean Git commits. "
        "Let me know if you would like to review the architecture notes before starting."
    )
    word_count = len(text_150_words.split())
    assert 80 <= word_count <= 180

    # Run humanizer
    humanized, audit = Humanizer.humanize_text(text_150_words)
    # Check rules engine audit
    re_audit = RulesEngine.audit_text(humanized)
    em_dash_violations = [v for v in re_audit["violations"] if "Rule 17" in v["rule"]]
    assert len(em_dash_violations) == 0, f"Expected 0 em-dash violations, got {em_dash_violations}"


def test_api_gigs_save_string_tags():
    """Verify that POST /api/gigs/save accepts string search_tags (comma-separated or JSON) without 422."""
    payload = {
        "platform": "fiverr",
        "title": "I will develop custom fastapi microservices",
        "category": "Programming & Tech",
        "search_tags": "fastapi, python, api, backend, postgresql",
        "description": "Clean, tested FastAPI services built for real traffic and low latency."
    }
    resp = client.post("/api/gigs/save", json=payload)
    assert resp.status_code == 200
    gig_id = resp.json()["gig_id"]

    # Verify saved gig has parsed tags list
    list_resp = client.get("/api/gigs/")
    assert list_resp.status_code == 200
    saved = [g for g in list_resp.json()["gigs"] if g["id"] == gig_id][0]
    assert isinstance(saved["search_tags"], list)
    assert "fastapi" in saved["search_tags"]

    # Cleanup
    client.delete(f"/api/gigs/{gig_id}")


def test_api_seo_audits_list_and_delete():
    """Verify listing SEO audits and deleting an audit via API."""
    # Insert a test SEO audit directly
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO seo_audits (gig_id, audit_type, score, recommendations, status)
        VALUES (NULL, 'deep_audit', 88.0, '["Add target keyword"]', 'completed')
    ''')
    audit_id = c.lastrowid
    conn.commit()
    conn.close()

    # List audits
    resp = client.get("/api/seo/audits")
    assert resp.status_code == 200
    audits = resp.json()["audits"]
    assert any(a["id"] == audit_id for a in audits)

    # Delete audit
    del_resp = client.delete(f"/api/seo/audits/{audit_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["status"] == "deleted"

    # Delete non-existent audit -> 404
    del_404 = client.delete(f"/api/seo/audits/{audit_id}")
    assert del_404.status_code == 404


def test_init_db_multiple_invocations():
    """Verify init_db can be called safely multiple times without leaking connections or failing."""
    init_db()
    init_db()
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM settings")
    count = c.fetchone()[0]
    conn.close()
    assert count > 0
