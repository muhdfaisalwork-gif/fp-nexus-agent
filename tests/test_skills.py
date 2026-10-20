import pytest
from core.skills.proposal_writer import ProposalWriter
from core.skills.gig_optimizer import GigOptimizer
from core.skills.inbox_handler import InboxHandler
from core.skills.project_uploader import ProjectUploader
from core.llm.client import UniversalLLMClient

class MockLLM:
    def generate(self, prompt, **kwargs):
        if "incoming client message" in prompt.lower():
            return """{
  "detected_intent": "pricing_inquiry",
  "recommended_action": "send_custom_offer",
  "reply_text": "I can deliver the custom scraper with proxy rotation for $150. Would you like me to send the custom offer now?",
  "suggested_price": 150
}"""
        elif "proposal" in prompt.lower():
            return """We can cut your order execution latency down to sub-400ms using an async FastAPI backend and Redis pub/sub queue.

On a previous trading platform, we reduced median order latency from 2,400ms to 380ms across 45,000 requests per minute by eliminating blocking database queries.

Here is the implementation plan:
1. Benchmark existing bottleneck endpoints using Locust.
2. Replace blocking synchronous ORM calls with async connection pooling.
3. Add a Redis cache layer for read-heavy market data.

Do you have your current endpoint latency traces available to review?"""
        elif "gig" in prompt.lower():
            return """{
  "title": "I will build a high speed python web scraper with playwright",
  "search_tags": ["python", "scraper", "playwright", "automation", "api"],
  "description": "I build custom web scrapers with playwright and python. Delivered with complete tests and documentation.",
  "basic_tier_name": "Starter",
  "basic_tier_desc": "Single site scraper",
  "basic_tier_price": 50,
  "basic_tier_delivery_days": 2,
  "standard_tier_name": "Standard",
  "standard_tier_desc": "Multi-page scraper with database export",
  "standard_tier_price": 150,
  "standard_tier_delivery_days": 4,
  "premium_tier_name": "Enterprise",
  "premium_tier_desc": "Production setup with proxy rotation and Docker",
  "premium_tier_price": 350,
  "premium_tier_delivery_days": 7,
  "faqs": [
    {"question": "How fast is delivery?", "answer": "Within 48 hours for the starter package."},
    {"question": "Do you provide test scripts?", "answer": "Yes, unit tests are included."},
    {"question": "Can you deploy to a server?", "answer": "Yes, Docker containers are provided."}
  ],
  "requirements": "Please share the target URLs and required data fields."
}"""
        else:
            return "Custom implementation details for the project."

def test_proposal_writer_with_mock():
    mock_llm = MockLLM()
    writer = ProposalWriter(llm_client=mock_llm)
    res = writer.draft_proposal(job_description="Need fast backend for order routing", platform_name="upwork")
    assert res["is_valid"] is True
    assert "FastAPI" in res["proposal_text"]
    assert "Dear hiring manager" not in res["proposal_text"].lower()
    assert res["word_count"] > 30

def test_gig_optimizer_with_mock():
    mock_llm = MockLLM()
    opt = GigOptimizer(llm_client=mock_llm)
    res = opt.optimize_gig(topic="Python Playwright Scraper", platform_name="fiverr")
    assert res["is_valid"] is True
    assert res["title"].startswith("I will")
    assert len(res["search_tags"]) == 5
    assert res["basic_tier_price"] >= 5

def test_inbox_handler_with_mock():
    mock_llm = MockLLM()
    handler = InboxHandler(llm_client=mock_llm)
    res = handler.reply_to_client("Can you do this for $100?")
    assert res["detected_intent"] == "pricing_inquiry"
    assert "custom offer" in res["reply_text"].lower()

def test_project_uploader_with_mock():
    mock_llm = MockLLM()
    uploader = ProjectUploader(llm_client=mock_llm)
    res = uploader.format_project_case_study(
        project_title="Order Processor",
        niche_or_category="Fintech",
        problem_solved="High latency",
        tech_stack="FastAPI, Redis",
        results_or_metrics="Cut latency to 380ms",
        deliverables="Docker compose",
        save_to_brain=True
    )
    assert res["saved_to_brain"] is True
    assert res["receipt_id"] is not None
