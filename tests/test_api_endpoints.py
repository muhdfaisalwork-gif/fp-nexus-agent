import pytest
from fastapi.testclient import TestClient
from api.app import app


client = TestClient(app)

def test_api_settings():
    res = client.get("/api/settings/")
    assert res.status_code == 200
    data = res.json()
    assert "settings" in data
    assert "supported_providers" in data

    update_res = client.post("/api/settings/", json={"DEFAULT_PLATFORM": "fiverr"})
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "updated"

def test_api_brain():
    res = client.get("/api/brain/receipts")
    assert res.status_code == 200
    data = res.json()
    assert "receipts" in data
    assert len(data["receipts"]) > 0

    # Add receipt
    add_res = client.post("/api/brain/receipts", json={
        "category": "API",
        "title": "FastAPI High-Load Microservice",
        "client_niche": "Fintech",
        "problem": "Legacy Flask service could not handle 10k req/min",
        "solution_stack": "FastAPI, Redis, PostgreSQL",
        "verified_metrics": "Latency dropped from 650ms to 42ms; 0 errors under peak load",
        "duration_days": 10,
        "deliverables": "Async endpoints, automated tests, Docker Compose"
    })
    assert add_res.status_code == 200
    receipt_id = add_res.json()["receipt_id"]

    # Delete receipt
    del_res = client.delete(f"/api/brain/receipts/{receipt_id}")
    assert del_res.status_code == 200
    assert del_res.json()["status"] == "deleted"

def test_api_profile():
    res = client.get("/api/profile/?platform=fiverr")
    assert res.status_code == 200
    assert "profile" in res.json()

    save_res = client.post("/api/profile/save", json={
        "platform": "fiverr",
        "username": "lucifer_dev",
        "title_headline": "Senior Full-Stack Engineer & Automation Architect",
        "bio_description": "Building resilient web applications and high-throughput scrapers.",
        "skills": ["Python", "FastAPI", "React", "Docker"],
        "languages": "English (Fluent)",
        "hourly_rate": 60.0
    })
    assert save_res.status_code == 200
    assert save_res.json()["status"] == "saved"

def test_api_gigs_save_list_delete():
    # Save a test gig
    save_res = client.post("/api/gigs/save", json={
        "platform": "fiverr",
        "title": "I will build a high-performance python fastapi backend",
        "category": "Programming & Tech",
        "subcategory": "Web Development",
        "search_tags": ["fastapi", "python api", "rest api", "backend", "docker"],
        "description": "I engineer production-grade REST APIs using FastAPI and PostgreSQL with clean documentation and tests.",
        "basic_tier_name": "Core API",
        "basic_tier_desc": "3 endpoints with sqlite",
        "basic_tier_price": 50.0,
        "basic_tier_delivery_days": 2,
        "seo_score": 92.0,
        "flesch_score": 68.0
    })
    assert save_res.status_code == 200
    gig_id = save_res.json()["gig_id"]

    # List gigs
    list_res = client.get("/api/gigs/")
    assert list_res.status_code == 200
    gigs = list_res.json()["gigs"]
    assert any(g["id"] == gig_id for g in gigs)

    # Audit the saved gig
    audit_res = client.post(f"/api/gigs/{gig_id}/audit")
    assert audit_res.status_code == 200
    assert "seo_score" in audit_res.json()

    # Delete gig
    del_res = client.delete(f"/api/gigs/{gig_id}")
    assert del_res.status_code == 200

def test_api_proposals_save_list():
    save_res = client.post("/api/proposals/save", json={
        "platform": "upwork",
        "job_title": "FastAPI Web Scraper Needed",
        "job_description": "We need a scraper for ecommerce catalog to extract 50k items daily.",
        "client_budget": "$500",
        "proposal_text": "I built a similar catalog pipeline extracting 80k products daily using Playwright and Redis. Here is how I will approach your catalog.",
        "humanizer_score": 98.0
    })
    assert save_res.status_code == 200
    prop_id = save_res.json()["proposal_id"]

    list_res = client.get("/api/proposals/")
    assert list_res.status_code == 200
    props = list_res.json()["proposals"]
    assert any(p["id"] == prop_id for p in props)

def test_api_seo_endpoints():
    from unittest.mock import patch
    audits_res = client.get("/api/seo/audits")
    assert audits_res.status_code == 200
    assert "audits" in audits_res.json()

    with patch("core.llm.client.UniversalLLMClient.generate", return_value="python-bot, web-scraper, playwright-api, automation-tool, fast-scraper"):
        refresh_res = client.post("/api/seo/weekly-refresh", json={
            "current_tags": ["python", "scraper", "automation", "api", "bots"],
            "gig_title": "I will build custom python scrapers and web automations",
            "gig_category": "Data & Scraping"
        })
        assert refresh_res.status_code == 200
        assert "recommended_tags" in refresh_res.json()

        scheduled_res = client.post("/api/seo/run-scheduled")
        assert scheduled_res.status_code == 200
        assert scheduled_res.json()["status"] == "success"

def test_api_inbox_history():
    res = client.get("/api/inbox/history")
    assert res.status_code == 200
    assert "conversations" in res.json()

def test_api_competitors_list():
    res = client.get("/api/competitors/")
    assert res.status_code == 200
    assert "scans" in res.json()
