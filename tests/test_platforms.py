import pytest
from core.platforms.factory import PlatformFactory
from core.platforms.fiverr import FiverrPlatform
from core.platforms.upwork import UpworkPlatform

def test_platform_factory():
    fiverr = PlatformFactory.get_platform("fiverr")
    assert isinstance(fiverr, FiverrPlatform)
    upwork = PlatformFactory.get_platform("upwork")
    assert isinstance(upwork, UpworkPlatform)

def test_fiverr_validation_success():
    fiverr = FiverrPlatform()
    valid_gig = {
        "title": "I will build a high speed python web scraper with playwright",
        "description": "I build custom python scrapers with robust anti-bot measures.",
        "search_tags": ["python", "scraper", "playwright", "automation", "api"],
        "basic_tier_price": 50,
        "standard_tier_price": 150,
        "premium_tier_price": 350
    }
    is_valid, errors = fiverr.validate_gig(valid_gig)
    assert is_valid is True
    assert len(errors) == 0

def test_fiverr_title_must_start_with_i_will():
    fiverr = FiverrPlatform()
    invalid_gig = {
        "title": "Python web scraper service for your business",
        "description": "Short description",
        "search_tags": ["python", "scraper"]
    }
    is_valid, errors = fiverr.validate_gig(invalid_gig)
    assert is_valid is False
    assert any("must start with 'I will'" in e for e in errors)

def test_fiverr_tag_limit():
    fiverr = FiverrPlatform()
    invalid_gig = {
        "title": "I will build custom python web scraper",
        "description": "Short description",
        "search_tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"] # 6 tags
    }
    is_valid, errors = fiverr.validate_gig(invalid_gig)
    assert is_valid is False
    assert any("maximum 5 search tags" in e for e in errors)

def test_upwork_proposal_hook_check():
    upwork = UpworkPlatform()
    fluffy_proposal = "Dear Hiring Manager, I hope you are well. I saw your job and I am thrilled to apply."
    is_valid, errors = upwork.validate_proposal(fluffy_proposal)
    assert is_valid is False
    assert any("contain fluff" in e for e in errors)
