from typing import Dict, Any, List, Tuple
from .base import BasePlatform

class FreelancerPlatform(BasePlatform):
    @property
    def platform_name(self) -> str:
        return "freelancer"

    def validate_gig(self, gig_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        issues = []
        title = (gig_data.get("title") or "").strip()
        desc = (gig_data.get("description") or "").strip()
        if not title:
            issues.append("Service title is required.")
        elif len(title) > 100:
            issues.append(f"Freelancer service title exceeds 100 characters limit ({len(title)} chars).")

        if not desc:
            issues.append("Service description is required.")
        elif len(desc) > 3000:
            issues.append(f"Freelancer service description exceeds 3000 characters limit ({len(desc)} chars).")

        return len(issues) == 0, issues

    def validate_proposal(self, proposal_text: str) -> Tuple[bool, List[str]]:
        issues = []
        clean = str(proposal_text or "").strip()
        if not clean:
            issues.append("Bid description cannot be empty.")
        elif len(clean) > 3000:
            issues.append(f"Freelancer bid description is too long ({len(clean)} chars).")
        return len(issues) == 0, issues

    def get_seo_rules(self) -> Dict[str, Any]:
        return {
            "title_max_len": 100,
            "desc_max_len": 3000,
            "max_skills": 5
        }

    def format_gig_markdown(self, gig_data: Dict[str, Any]) -> str:
        title = gig_data.get("title", "")
        desc = gig_data.get("description", "")
        return f"# Freelancer Service: {title}\n\n{desc}"
