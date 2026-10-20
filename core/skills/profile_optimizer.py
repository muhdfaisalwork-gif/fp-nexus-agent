import json
import re
from typing import Dict, Any, List, Optional
from core.llm.client import UniversalLLMClient
from core.brain.brain import BrainManager
from core.rules.rules_engine import RulesEngine
from core.rules.humanizer import Humanizer
from core.platforms.factory import PlatformFactory

class ProfileOptimizer:
    """
    Optimizes freelancer profiles for Fiverr (Bio/Description, Headline, Skills)
    and Upwork (Overview, Title, Specialised Profiles).
    """

    def __init__(self, llm_client: Optional[UniversalLLMClient] = None, brain: Optional[BrainManager] = None):
        self.llm = llm_client or UniversalLLMClient()
        self.brain = brain or BrainManager()

    def optimize_profile(
        self,
        primary_role: str,
        core_skills: List[str],
        years_experience: int = 5,
        platform_name: str = "fiverr",
        specialty_niche: str = ""
    ) -> Dict[str, Any]:
        if isinstance(core_skills, str):
            core_skills = [s.strip() for s in core_skills.split(",") if s.strip()]
        elif not isinstance(core_skills, list):
            core_skills = list(core_skills) if core_skills else []

        platform = PlatformFactory.get_platform(platform_name)
        receipts = self.brain.get_receipts(limit=3)
        receipts_text = self.brain.format_receipts_for_prompt(receipts)

        system_prompt = RulesEngine.get_system_prompt()
        prompt = f"""You are a freelance branding and conversion strategist for {platform.platform_name.upper()}.
Generate an authoritative, human-sounding freelancer profile that passes all 82 humanizer rules.
NO AI fluff (no 'passionate developer', 'innovative solutions', 'delve into', 'robust architectures').
Write like a pragmatic builder with real commercial experience.

ROLE: {primary_role}
CORE SKILLS: {', '.join(str(s) for s in core_skills)}
YEARS EXPERIENCE: {years_experience}
SPECIALTY: {specialty_niche or primary_role}

{receipts_text}

OUTPUT FORMAT (JSON ONLY):
{{
  "headline": "Punchy professional headline under 70 characters",
  "bio_summary": "1-2 paragraphs for Fiverr profile description or Upwork overview (under 600 chars for Fiverr). Direct, confident, mentions concrete stacks and real outcomes.",
  "recommended_skills": ["skill1", "skill2", "skill3", "skill4", "skill5", "skill6", "skill7", "skill8"],
  "specialization_tags": ["tag1", "tag2", "tag3", "tag4"]
}}
"""
        raw_output = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.6, max_tokens=1000)

        data = {}
        match = re.search(r'\{[\s\S]*\}', str(raw_output or ""))
        if match:
            try:
                data = json.loads(match.group(0))
            except Exception:
                pass

        if not data:
            data = {
                "headline": f"Full-Stack {primary_role} | Python & Web Architecture",
                "bio_summary": f"I build fast, scalable applications using {', '.join(str(s) for s in core_skills[:3])}. Over {years_experience} years shipping production software with clean code and clear documentation.",
                "recommended_skills": core_skills,
                "specialization_tags": core_skills[:4]
            }

        # Handle alternate key names from model fallbacks or variants
        if not data.get("headline") and data.get("title_headline"):
            data["headline"] = data["title_headline"]
        if not data.get("bio_summary") and data.get("bio_description"):
            data["bio_summary"] = data["bio_description"]
        if not data.get("recommended_skills") and data.get("skills"):
            data["recommended_skills"] = data["skills"]

        if "recommended_skills" not in data or not data["recommended_skills"]:
            data["recommended_skills"] = core_skills
        if "specialization_tags" not in data or not data["specialization_tags"]:
            data["specialization_tags"] = core_skills[:4]

        bio_clean, audit = Humanizer.humanize_text(data.get("bio_summary") or "")
        data["bio_summary"] = bio_clean
        data["title_headline"] = data.get("headline", "")
        data["bio_description"] = bio_clean
        data["humanizer_audit"] = audit
        data["platform"] = platform.platform_name
        return data
