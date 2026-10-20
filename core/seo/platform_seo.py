import re
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
from core.rules.rules_engine import RulesEngine
from core.llm.client import UniversalLLMClient

class PlatformSEO:
    """
    Freelance Platform SEO & Algorithmic Ranking Engine:
    - Calculates quantitative SEO Score (0-100) based on title, tags, description density, and FAQs.
    - Weekly Keyword Refresh: updates low-performing search tags.
    - Bi-Weekly Deep Audit: 14-day algorithmic freshness audit and rewrite recommendations.
    """

    def __init__(self, llm_client: Optional[UniversalLLMClient] = None):
        self.llm = llm_client or UniversalLLMClient()

    def audit_gig_seo(self, gig_data: Dict[str, Any], primary_keyword: str = "") -> Dict[str, Any]:
        title = (gig_data.get("title") or "").strip()
        desc = (gig_data.get("description") or "").strip()
        tags = gig_data.get("search_tags")
        if tags is None:
            tags = []
        elif isinstance(tags, str):
            tags_str = tags.strip()
            if tags_str.startswith("["):
                try:
                    loaded = json.loads(tags_str)
                    tags = loaded if isinstance(loaded, list) else [t.strip() for t in tags_str.split(",") if t.strip()]
                except Exception:
                    tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            else:
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        elif not isinstance(tags, list):
            try:
                tags = list(tags)
            except Exception:
                tags = []

        score = 100
        checklist = []
        issues = []
        recommendations = []

        # Auto-detect primary keyword from title if not given
        if not primary_keyword and title:
            # Strip 'I will build/create'
            kw_candidate = re.sub(r'^i will (build|create|develop|code|design|do)?\s*', '', title, flags=re.IGNORECASE)
            primary_keyword = kw_candidate.strip().lower()

        pk_lower = primary_keyword.lower() if primary_keyword else ""

        # 1. Title SEO Audit (Max 20 pts)
        title_len = len(title)
        if not title:
            score -= 20
            checklist.append({"item": "Gig Title", "status": "fail", "note": "Title is missing."})
        elif title_len > 75:
            score -= 8
            checklist.append({"item": "Gig Title Length", "status": "warning", "note": f"Title is {title_len} chars. Optimal for mobile is 45-70 chars."})
            recommendations.append("Shorten title to keep it visible on mobile search results without truncation.")
        elif title_len < 30:
            score -= 8
            checklist.append({"item": "Gig Title Length", "status": "warning", "note": "Title is too short to rank for multiple buyer queries."})
        else:
            checklist.append({"item": "Gig Title Length", "status": "pass", "note": f"Optimal length ({title_len} chars)."})

        if pk_lower and pk_lower in title.lower():
            checklist.append({"item": "Primary Keyword in Title", "status": "pass", "note": f"Found '{primary_keyword}' in title."})
        else:
            score -= 10
            checklist.append({"item": "Primary Keyword in Title", "status": "warning", "note": "Primary keyword not explicitly present in title."})
            recommendations.append(f"Include primary keyword '{primary_keyword}' in the gig title.")

        # 2. Search Tags Audit (Max 20 pts)
        tag_count = len(tags)
        if tag_count == 5:
            checklist.append({"item": "Tag Count", "status": "pass", "note": "All 5 search tags utilized."})
        elif tag_count > 0:
            score -= (5 - tag_count) * 4
            checklist.append({"item": "Tag Count", "status": "warning", "note": f"Using only {tag_count}/5 tags. Fiverr allows 5 tags."})
            recommendations.append(f"Add {5 - tag_count} more high-intent search tags to maximize search impressions.")
        else:
            score -= 20
            checklist.append({"item": "Tag Count", "status": "fail", "note": "Zero search tags found."})

        # Check tag lengths & characters
        for t in tags:
            t_str = str(t if t is not None else "").strip()
            if len(t_str) > 20:
                score -= 3
                issues.append(f"Tag '{t_str}' exceeds 20 characters limit.")

        # 3. Description Keyword Density (Max 25 pts)
        desc_len = len(desc)
        if not desc:
            score -= 25
            checklist.append({"item": "Description Content", "status": "fail", "note": "Description is empty."})
        else:
            # Check primary keyword in first 100 chars
            first_100 = desc[:120].lower()
            if pk_lower and pk_lower in first_100:
                checklist.append({"item": "Keyword in First 100 Chars", "status": "pass", "note": "Primary keyword appears early in description."})
            elif pk_lower:
                score -= 8
                checklist.append({"item": "Keyword in First 100 Chars", "status": "warning", "note": "Primary keyword missing from opening 100 characters."})
                recommendations.append("Place your primary target keyword in the first sentence of your description.")

            # Calculate keyword density
            words = re.findall(r'\b\w+\b', desc.lower())
            word_count = len(words)
            if pk_lower:
                left = r'\b' if pk_lower[0].isalnum() or pk_lower[0] == '_' else r'(?<!\S)'
                right = r'\b' if pk_lower[-1].isalnum() or pk_lower[-1] == '_' else r'(?!\S)'
                kw_count = len(re.findall(left + re.escape(pk_lower) + right, desc.lower()))
            else:
                kw_count = 0
            density = round((kw_count / word_count) * 100, 2) if word_count > 0 else 0.0

            if 1.0 <= density <= 3.0:
                checklist.append({"item": "Keyword Density", "status": "pass", "note": f"Ideal keyword density ({density}%)."})
            elif density > 3.0:
                score -= 6
                checklist.append({"item": "Keyword Density", "status": "warning", "note": f"Keyword density ({density}%) may risk keyword stuffing penalties."})
                recommendations.append("Reduce repetitive keyword mentions to maintain natural readability.")
            else:
                score -= 6
                checklist.append({"item": "Keyword Density", "status": "warning", "note": f"Low keyword density ({density}%)."})

        # 4. Humanizer & Quality Check (Max 20 pts)
        humanizer_audit = RulesEngine.audit_text(desc)
        if not humanizer_audit.get("is_compliant", True):
            score -= 12
            checklist.append({"item": "Humanizer Anti-Slop Audit", "status": "fail", "note": f"Found {len(humanizer_audit.get('violations', []))} AI tells in description."})
            recommendations.append("Scrub forbidden AI buzzwords from description to avoid algorithmic quality penalties.")
        else:
            checklist.append({"item": "Humanizer Anti-Slop Audit", "status": "pass", "note": "100% human-natural prose without AI tells."})

        # 5. FAQ and Packages (Max 15 pts)
        faqs = gig_data.get("faqs", [])
        if faqs and len(faqs) >= 3:
            checklist.append({"item": "FAQs Coverage", "status": "pass", "note": f"{len(faqs)} FAQs present."})
        else:
            score -= 8
            checklist.append({"item": "FAQs Coverage", "status": "warning", "note": "Adding at least 3 FAQs improves gig dwell time and search ranking."})
            recommendations.append("Add 3 detailed FAQs addressing common buyer objections.")

        score = max(0, min(100, score))

        return {
            "seo_score": score,
            "primary_keyword": primary_keyword,
            "checklist": checklist,
            "issues": issues,
            "recommendations": recommendations,
            "density_pct": density if 'density' in locals() else 0.0,
            "flesch_score": humanizer_audit.get("flesch_score", 70.0)
        }

    def weekly_keyword_refresh(self, current_tags: List[str], gig_title: str, gig_category: str) -> Dict[str, Any]:
        """Generates fresh, high-intent keyword substitutions for weekly ranking rotation."""
        if current_tags is None:
            current_tags = []
        elif isinstance(current_tags, str):
            tags_str = current_tags.strip()
            if tags_str.startswith("["):
                try:
                    loaded = json.loads(tags_str)
                    current_tags = loaded if isinstance(loaded, list) else [t.strip() for t in tags_str.split(",") if t.strip()]
                except Exception:
                    current_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
            else:
                current_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        elif not isinstance(current_tags, list):
            try:
                current_tags = list(current_tags)
            except Exception:
                current_tags = []

        prompt = f"""You are an algorithmic search ranking specialist for Fiverr and Upwork.
Analyze these current gig search tags and suggest a fresh set of 5 high-intent, low-competition buyer search tags to refresh search indexing.

GIG TITLE: {gig_title}
CATEGORY: {gig_category}
CURRENT TAGS: {', '.join(str(t) for t in current_tags)}

Provide exactly 5 replacement tags that buyers search for when purchasing (transactional intent).
Tags must be under 20 characters each. Return ONLY a comma-separated list of 5 tags.
"""
        raw_output = self.llm.generate(prompt=prompt, temperature=0.7, max_tokens=250) or ""
        candidates = [t.strip().lower() for t in raw_output.replace("\n", "").split(",") if t.strip()]

        new_tags = []
        for c in candidates:
            # Strip list numbers, bullets, brackets, and invalid symbols
            cleaned = re.sub(r'^\d+[\.\)]\s*', '', c)
            cleaned = re.sub(r'[^a-zA-Z0-9\s\-]', '', cleaned).strip().lower()
            if cleaned and len(cleaned) <= 20 and cleaned not in new_tags:
                new_tags.append(cleaned)

        # Pad to 5 if needed
        if len(new_tags) < 5:
            fallbacks = ["api development", "fastapi", "python automation", "backend dev", "web scraper"]
            for fb in fallbacks:
                if len(new_tags) >= 5:
                    break
                if fb not in new_tags:
                    new_tags.append(fb)

        new_tags = new_tags[:5]

        return {
            "previous_tags": current_tags,
            "recommended_tags": new_tags,
            "rationale": "Rotating search tags weekly signals algorithmic freshness to the platform search index without altering gig URL."
        }

    def biweekly_deep_scan(self, gig_data: Dict[str, Any]) -> Dict[str, Any]:
        """Runs full 14-day algorithmic SEO audit, proposing revised tags, headline, and FAQ updates."""
        audit = self.audit_gig_seo(gig_data)
        refresh = self.weekly_keyword_refresh(
            current_tags=gig_data.get("search_tags", []),
            gig_title=gig_data.get("title", ""),
            gig_category=gig_data.get("category", "")
        )

        return {
            "audit_type": "biweekly_deep_scan",
            "current_seo_score": audit["seo_score"],
            "checklist": audit["checklist"],
            "recommendations": audit["recommendations"],
            "recommended_tags": refresh["recommended_tags"],
            "suggested_refresh_date": (datetime.now(timezone.utc) + timedelta(days=14)).strftime("%Y-%m-%d")
        }
