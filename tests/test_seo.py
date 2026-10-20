import pytest
from core.seo.platform_seo import PlatformSEO

class DummyLLM:
    def generate(self, prompt, **kwargs):
        return "python-bot, web-scraper, playwright-api, automation-tool, fast-scraper"

def test_audit_gig_seo():
    seo = PlatformSEO(llm_client=DummyLLM())
    gig_data = {
        "title": "I will build a high speed python web scraper with playwright",
        "description": "I build a high speed python web scraper for data extraction. Delivered with complete documentation and Docker setup.",
        "search_tags": ["python", "scraper", "playwright", "automation", "api"],
        "faqs": [
            {"question": "How fast is delivery?", "answer": "Usually within 48 hours."},
            {"question": "Do you handle pagination?", "answer": "Yes, pagination and dynamic loading are supported."},
            {"question": "Can this run on a VPS?", "answer": "Yes, Docker containers are included."}
        ]
    }
    audit = seo.audit_gig_seo(gig_data, primary_keyword="python web scraper")
    assert audit["seo_score"] >= 80
    assert len(audit["checklist"]) >= 4

def test_weekly_keyword_refresh():
    seo = PlatformSEO(llm_client=DummyLLM())
    res = seo.weekly_keyword_refresh(
        current_tags=["tag1", "tag2"],
        gig_title="I will build python scraper",
        gig_category="Programming"
    )
    assert len(res["recommended_tags"]) == 5
    assert "rationale" in res
