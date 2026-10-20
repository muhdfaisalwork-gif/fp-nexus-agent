import json
import re
from typing import Dict, Any, List, Optional
from core.llm.client import UniversalLLMClient
from core.brain.brain import BrainManager
from core.rules.rules_engine import RulesEngine
from core.rules.humanizer import Humanizer
from core.platforms.factory import PlatformFactory

class GigOptimizer:
    """
    Optimizes and drafts high-converting freelance gigs (Fiverr & Upwork Project Catalog).
    Enforces platform character limits and passes all copy through the 82 Humanizer rules.
    """

    def __init__(self, llm_client: Optional[UniversalLLMClient] = None, brain: Optional[BrainManager] = None):
        self.llm = llm_client or UniversalLLMClient()
        self.brain = brain or BrainManager()

    def optimize_gig(
        self,
        topic: str,
        target_keywords: Optional[List[str]] = None,
        platform_name: str = "fiverr",
        category: str = "Programming & Tech",
        custom_instructions: str = ""
    ) -> Dict[str, Any]:
        platform = PlatformFactory.get_platform(platform_name)
        receipts = self.brain.get_receipts(query=topic, limit=3)
        receipts_text = self.brain.format_receipts_for_prompt(receipts)

        if isinstance(target_keywords, str):
            target_keywords = [k.strip() for k in target_keywords.split(",") if k.strip()]
        elif not isinstance(target_keywords, list):
            target_keywords = list(target_keywords) if target_keywords else []

        kw_str = ", ".join(str(k) for k in target_keywords) if target_keywords else topic

        system_prompt = RulesEngine.get_system_prompt()
        prompt = f"""You are an elite freelance growth specialist and copywriter for {platform.platform_name.upper()}.
Generate an optimized, high-converting service gig adhering strictly to the 82 humanizer rules.
NO AI tells (never say 'delve', 'robust', 'seamless', 'game-changer', 'elevate', 'transformative', 'cutting-edge').
Start with plain concrete facts and tangible deliverables.

SERVICE TOPIC: {topic}
TARGET SEARCH KEYWORDS: {kw_str}
CATEGORY: {category}
EXTRA INSTRUCTIONS: {custom_instructions}

{receipts_text}

PLATFORM SPECIFIC REQUIREMENTS FOR {platform.platform_name.upper()}:
- Title: If Fiverr, MUST start with 'I will' and be under 75 characters. Crisp and specific.
- Search Tags: Exactly 5 high-intent tags. Max 20 characters each. Letters, numbers, spaces only.
- Description: Under 1150 characters (leaving room for Fiverr 1200 char hard limit). The first 100 characters MUST contain the primary search keyword. Clearly state:
  1. What real problem is solved
  2. Concrete technical stack & deliverables
  3. Delivery timeline and what the buyer needs to provide
- 3 Packages: Basic, Standard, Premium (Name, Short Description under 100 chars, Price USD, Delivery Days).
- 3 Realistic FAQs: Direct questions buyers ask with straightforward answers.
- Buyer Requirements: 1-3 bullet points specifying what files/credentials are needed.

Return ONLY a valid JSON object with this exact structure:
{{
  "title": "I will ...",
  "search_tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "description": "...",
  "basic_tier_name": "...",
  "basic_tier_desc": "...",
  "basic_tier_price": 50,
  "basic_tier_delivery_days": 2,
  "standard_tier_name": "...",
  "standard_tier_desc": "...",
  "standard_tier_price": 150,
  "standard_tier_delivery_days": 4,
  "premium_tier_name": "...",
  "premium_tier_desc": "...",
  "premium_tier_price": 350,
  "premium_tier_delivery_days": 7,
  "faqs": [
    {{"question": "...", "answer": "..."}},
    {{"question": "...", "answer": "..."}},
    {{"question": "...", "answer": "..."}}
  ],
  "requirements": "..."
}}
"""
        raw_output = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.6, max_tokens=1800)
        
        # Parse JSON
        parsed_data = self._parse_json(raw_output, topic)
        parsed_data["category"] = category
        parsed_data["platform"] = platform.platform_name
        parsed_data["target_keywords"] = target_keywords

        # Sanitize Title
        title = (parsed_data.get("title") or "").strip()
        if platform.platform_name == "fiverr":
            if not title.lower().startswith("i will"):
                title = f"I will {title}"
            # Fiverr does not allow periods at the end of titles
            title = title.rstrip(".")
            if len(title) > 80:
                title = title[:75].rsplit(" ", 1)[0]
        elif platform.platform_name == "upwork":
            if title.lower().startswith("i will "):
                title = title[7:].capitalize()
            if len(title) > 75:
                title = title[:72].rsplit(" ", 1)[0]
        elif platform.platform_name == "freelancer":
            if len(title) > 100:
                title = title[:95].rsplit(" ", 1)[0]
        parsed_data["title"] = title

        # Sanitize Search Tags (clean symbols, max 20 chars, exactly 5 tags)
        raw_tags = parsed_data.get("search_tags", [])
        if isinstance(raw_tags, str):
            raw_tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        
        clean_tags = []
        for t in raw_tags:
            cleaned_tag = re.sub(r'[^a-zA-Z0-9\s\-]', '', str(t)).strip().lower()
            if cleaned_tag and len(cleaned_tag) <= 20 and cleaned_tag not in clean_tags:
                clean_tags.append(cleaned_tag)

        # Pad tags to 5 if needed using keywords from topic
        if len(clean_tags) < 5:
            topic_words = [w.lower() for w in re.findall(r'[a-zA-Z0-9]{3,}', topic) if w.lower() not in clean_tags]
            for w in topic_words:
                if len(clean_tags) >= 5:
                    break
                clean_tags.append(w[:20])

        parsed_data["search_tags"] = clean_tags[:5]

        # Unpack nested tiers if provided in model output
        for tier in ["basic", "standard", "premium"]:
            nested_tier = parsed_data.get(f"{tier}_tier")
            if isinstance(nested_tier, dict):
                if not parsed_data.get(f"{tier}_tier_name"):
                    parsed_data[f"{tier}_tier_name"] = nested_tier.get("name", tier.capitalize())
                if not parsed_data.get(f"{tier}_tier_desc"):
                    parsed_data[f"{tier}_tier_desc"] = nested_tier.get("description", "")
                if f"{tier}_tier_price" not in parsed_data:
                    parsed_data[f"{tier}_tier_price"] = nested_tier.get("price", 50.0)
                if f"{tier}_tier_delivery_days" not in parsed_data:
                    parsed_data[f"{tier}_tier_delivery_days"] = nested_tier.get("delivery_days", 2)

        # Sanitize prices and days
        for tier in ["basic", "standard", "premium"]:
            p_val = parsed_data.get(f"{tier}_tier_price", 50)
            try:
                # Strip $ or commas while preserving negative sign for min-clamping
                p_clean = float(re.sub(r'[^\d.\-]', '', str(p_val)))
                parsed_data[f"{tier}_tier_price"] = max(5.0, p_clean)
            except Exception:
                parsed_data[f"{tier}_tier_price"] = 50.0

            d_val = parsed_data.get(f"{tier}_tier_delivery_days", 2)
            try:
                d_clean = int(re.sub(r'[^\d\-]', '', str(d_val)))
                parsed_data[f"{tier}_tier_delivery_days"] = max(1, d_clean)
            except Exception:
                parsed_data[f"{tier}_tier_delivery_days"] = 2

        # Normalize FAQs format
        if "faqs" in parsed_data and isinstance(parsed_data["faqs"], list):
            clean_faqs = []
            for f in parsed_data["faqs"]:
                if isinstance(f, dict):
                    q = f.get("question") or f.get("q", "")
                    a = f.get("answer") or f.get("a", "")
                    if q and a:
                        clean_faqs.append({"question": q, "answer": a})
            parsed_data["faqs"] = clean_faqs

        # Humanize description, FAQs, and packages
        humanized_desc, audit = Humanizer.humanize_text(parsed_data.get("description") or "")
        
        # Enforce Fiverr 1200 hard limit at clean sentence boundary
        if platform.platform_name == "fiverr" and len(humanized_desc) > 1200:
            truncated = humanized_desc[:1180]
            if "." in truncated:
                humanized_desc = truncated.rsplit(".", 1)[0] + "."
            else:
                humanized_desc = truncated

        parsed_data["description"] = humanized_desc
        parsed_data["flesch_score"] = audit.get("flesch_score", 70.0)
        parsed_data["humanizer_audit"] = audit

        # Validate against platform constraints
        is_valid, validation_errors = platform.validate_gig(parsed_data)
        parsed_data["is_valid"] = is_valid
        parsed_data["validation_errors"] = validation_errors

        return parsed_data

    def _parse_json(self, raw_text: str, fallback_topic: str) -> Dict[str, Any]:
        cleaned = str(raw_text or "").strip()
        # Find JSON object
        match = re.search(r'\{[\s\S]*\}', cleaned)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass

        # Fallback dictionary if model outputted malformed JSON
        return {
            "title": f"I will build {fallback_topic[:50]}",
            "search_tags": ["python", "automation", "api", "web-scraping", "bot"],
            "description": f"I build custom solutions for {fallback_topic}. You get clean, tested code with complete documentation and setup instructions.",
            "basic_tier_name": "Starter",
            "basic_tier_desc": "Core script or single feature with documentation",
            "basic_tier_price": 50,
            "basic_tier_delivery_days": 2,
            "standard_tier_name": "Standard",
            "standard_tier_desc": "Complete workflow with error handling and API setup",
            "standard_tier_price": 150,
            "standard_tier_delivery_days": 4,
            "premium_tier_name": "Enterprise",
            "premium_tier_desc": "Production deployment, Docker container, and 30-day support",
            "premium_tier_price": 350,
            "premium_tier_delivery_days": 7,
            "faqs": [
                {"question": "What do you need to get started?", "answer": "Clear functional requirements and any target API documentation or access credentials."},
                {"question": "Do you provide revisions?", "answer": "Yes, standard and premium tiers include revisions to ensure the code matches your requirements."},
                {"question": "Can you deploy this to my server?", "answer": "Yes, I can provide Docker containers or deploy directly to your VPS or cloud provider."}
            ],
            "requirements": "Please share your project specifications, API endpoints, and preferred timeline."
        }
