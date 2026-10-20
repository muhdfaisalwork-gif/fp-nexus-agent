import pytest
from unittest.mock import MagicMock
from core.reach.scanner import CompetitorScanner
from core.rules.humanizer import Humanizer
from core.skills.gig_optimizer import GigOptimizer
from core.skills.profile_optimizer import ProfileOptimizer
from core.seo.platform_seo import PlatformSEO
from starlette.testclient import TestClient
from api.app import app

def test_competitor_scanner_safe_number_parsing():
    mock_reader = MagicMock()
    mock_reader.read_url.return_value = {
        "status": "success",
        "title": "Top Python Scraper Gig",
        "content": "Professional web scraping and API automation."
    }

    mock_llm = MagicMock()
    mock_llm.generate.return_value = '''
    {
      "competitor_name": "ProDev",
      "gig_title": "I will build python web scraper",
      "price_range": "$50 - $300",
      "extracted_tags": "python, scraper, api, bots",
      "review_count": "1,450+ reviews",
      "rating": "4.9 / 5.0 stars",
      "buyer_pain_points_or_gaps": "No unit tests provided",
      "counter_strategy": "Offer full pytest suites and Docker"
    }
    '''

    scanner = CompetitorScanner(reader=mock_reader, llm=mock_llm)
    result = scanner.scan_competitor_url("https://www.fiverr.com/prodev/scraper")

    assert result["status"] == "success"
    assert result["review_count"] == 1450
    assert result["rating"] == 4.9
    assert isinstance(result["extracted_tags"], list)
    assert "python" in result["extracted_tags"]

def test_humanizer_em_dash_punctuation_edge_cases():
    # Text with 10 words and 3 em-dashes in messy punctuation contexts
    # Allowed dashes for 10 words is 1
    raw = 'Fast service (tested) — "reliable backend" -- zero errors — guaranteed.'
    cleaned, audit = Humanizer.humanize_text(raw)
    dashes_left = cleaned.count("—") + cleaned.count("--")
    assert dashes_left <= 1

def test_gig_optimizer_fiverr_length_trimming():
    mock_llm = MagicMock()
    # Generate a description that is 1400 characters long
    long_desc = ("I build production-grade web systems. " * 35)
    assert len(long_desc) > 1200

    mock_llm.generate.return_value = f'''
    {{
      "title": "I will build production grade python fastapi microservices",
      "search_tags": ["fastapi", "python", "rest api", "backend", "docker"],
      "description": "{long_desc}",
      "basic_tier_name": "Core",
      "basic_tier_desc": "Basic endpoint",
      "basic_tier_price": 50,
      "basic_tier_delivery_days": 2,
      "standard_tier_name": "Standard",
      "standard_tier_desc": "Standard api",
      "standard_tier_price": 150,
      "standard_tier_delivery_days": 4,
      "premium_tier_name": "Enterprise",
      "premium_tier_desc": "Production setup",
      "premium_tier_price": 350,
      "premium_tier_delivery_days": 7,
      "faqs": [],
      "requirements": "Docs"
    }}
    '''

    optimizer = GigOptimizer(llm_client=mock_llm)
    result = optimizer.optimize_gig(topic="FastAPI Microservices", platform_name="fiverr")

    assert len(result["description"]) <= 1200
    assert result["is_valid"] is True
    assert not any("1200 characters" in e for e in result["validation_errors"])

def test_profile_optimizer_keys():
    mock_llm = MagicMock()
    mock_llm.generate.return_value = '''
    {
      "headline": "Senior Full-Stack Engineer & Automation Architect",
      "bio_summary": "I engineer high-throughput web backends and resilient scrapers.",
      "recommended_skills": ["Python", "FastAPI", "React", "Docker"],
      "specialization_tags": ["APIs", "Automation"]
    }
    '''
    prof_opt = ProfileOptimizer(llm_client=mock_llm)
    result = prof_opt.optimize_profile(primary_role="Full-Stack Engineer", core_skills=["Python", "FastAPI"])

    assert "headline" in result
    assert "title_headline" in result
    assert "bio_summary" in result
    assert "bio_description" in result
    assert result["title_headline"] == "Senior Full-Stack Engineer & Automation Architect"

def test_platform_seo_weekly_tags_sanitization():
    mock_llm = MagicMock()
    # Output tags with numbers, bullet points, brackets, and an overly long tag
    mock_llm.generate.return_value = "1. [fastapi], 2. -python api-, 3. backend architecture and microservice development, 4. rest api, 5. postgresql"

    seo = PlatformSEO(llm_client=mock_llm)
    result = seo.weekly_keyword_refresh(
        current_tags=["fastapi", "python"],
        gig_title="FastAPI Development",
        gig_category="Programming"
    )

    tags = result["recommended_tags"]
    assert len(tags) == 5
    for t in tags:
        assert len(t) <= 20
        assert not t.startswith("1.")
        assert "[" not in t and "]" not in t

def test_list_gigs_returns_faqs_and_requirements():
    client = TestClient(app)
    # Save gig with faqs and requirements
    save_res = client.post("/api/gigs/save", json={
        "platform": "fiverr",
        "title": "I will engineer clean python scripts and automations",
        "category": "Programming & Tech",
        "subcategory": "Python",
        "search_tags": ["python", "scripts", "bot", "automation", "api"],
        "description": "I engineer tested Python scripts for data processing and automated workflows.",
        "faqs": [{"question": "Do you provide setup guides?", "answer": "Yes, complete instructions are included."}],
        "requirements": "Provide your input files and target output format."
    })
    assert save_res.status_code == 200
    gig_id = save_res.json()["gig_id"]

    list_res = client.get("/api/gigs/")
    assert list_res.status_code == 200
    gigs = list_res.json()["gigs"]
    saved_gig = next((g for g in gigs if g["id"] == gig_id), None)
    assert saved_gig is not None
    assert "faqs" in saved_gig
    assert "requirements" in saved_gig
    assert len(saved_gig["faqs"]) == 1
    assert saved_gig["requirements"] == "Provide your input files and target output format."

    # Clean up
    client.delete(f"/api/gigs/{gig_id}")
