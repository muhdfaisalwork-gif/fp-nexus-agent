from typing import Dict, Any, List, Tuple
from .base import BasePlatform

class UpworkPlatform(BasePlatform):
    @property
    def platform_name(self) -> str:
        return "upwork"

    def validate_gig(self, gig_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        # Upwork Project Catalog rules
        issues = []
        title = (gig_data.get("title") or "").strip()
        desc = (gig_data.get("description") or "").strip()

        if not title:
            issues.append("Project catalog title is required.")
        elif len(title) > 75:
            issues.append(f"Upwork project title exceeds 75 characters limit ({len(title)} chars).")

        if not desc:
            issues.append("Project description is required.")
        elif len(desc) > 4000:
            issues.append(f"Upwork project description exceeds 4000 characters limit ({len(desc)} chars).")

        return len(issues) == 0, issues

    def validate_proposal(self, proposal_text: str) -> Tuple[bool, List[str]]:
        issues = []
        clean = str(proposal_text or "").strip()
        if not clean:
            issues.append("Proposal cover letter cannot be empty.")
        if len(clean) > 5000:
            issues.append(f"Upwork proposal exceeds 5000 characters limit ({len(clean)} chars).")

        # Crucial Upwork rule: First 200 characters are the visible preview in the client's proposal list
        first_200 = clean[:200].lower()
        if any(w in first_200 for w in ["dear hiring manager", "hope you are well", "thrilled to apply", "excited to bid"]):
            issues.append("First 200 characters contain fluff. Upwork clients only see this snippet before opening your bid.")

        return len(issues) == 0, issues

    def get_seo_rules(self) -> Dict[str, Any]:
        return {
            "title_max_len": 75,
            "title_optimal_len": 55,
            "desc_max_len": 4000,
            "first_200_chars_critical": True,
            "max_skills": 10
        }

    def format_gig_markdown(self, gig_data: Dict[str, Any]) -> str:
        title = gig_data.get("title", "")
        desc = gig_data.get("description", "")
        tags = gig_data.get("search_tags") or ""
        if isinstance(tags, list):
            tags = ", ".join(str(t) for t in tags)

        return f"""# Upwork Project Catalog: {title}

**Skills / Tags:** {tags}

## Project Overview
{desc}
"""
