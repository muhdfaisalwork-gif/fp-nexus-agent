import re
from typing import Dict, Any, List, Tuple
from .base import BasePlatform

class FiverrPlatform(BasePlatform):
    @property
    def platform_name(self) -> str:
        return "fiverr"

    def validate_gig(self, gig_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        issues = []
        title = (gig_data.get("title") or "").strip()
        desc = (gig_data.get("description") or "").strip()
        tags = gig_data.get("search_tags", [])

        # 1. Title validation
        if not title:
            issues.append("Gig title is required.")
        else:
            if not title.lower().startswith("i will"):
                issues.append("Fiverr gig titles must start with 'I will'.")
            if title.endswith("."):
                issues.append("Fiverr gig titles cannot end with a period ('.').")
            if len(title) > 80:
                issues.append(f"Fiverr title exceeds 80 characters limit ({len(title)} chars). Keep under 70 for best search visibility.")

        # 2. Description validation (Fiverr max 1200 chars)
        if not desc:
            issues.append("Gig description is required.")
        elif len(desc) > 1200:
            issues.append(f"Fiverr description exceeds 1200 characters limit ({len(desc)} chars).")

        # 3. Tags validation (Exactly 5 tags, max 20 chars per tag)
        if isinstance(tags, str):
            tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        elif isinstance(tags, list):
            tag_list = tags
        else:
            tag_list = []

        if len(tag_list) > 5:
            issues.append(f"Fiverr allows maximum 5 search tags (found {len(tag_list)}).")
        for tag in tag_list:
            tag_str = str(tag).strip()
            if len(tag_str) > 20:
                issues.append(f"Tag '{tag_str}' exceeds 20 characters limit.")
            if not re.match(r'^[a-zA-Z0-9\s\-]+$', tag_str):
                issues.append(f"Tag '{tag_str}' contains invalid symbols. Only letters, numbers, and spaces allowed.")

        # 4. Pricing tiers & delivery days validation
        pricing_tiers_dict = gig_data.get("pricing_tiers") or {}
        for tier in ["basic", "standard", "premium"]:
            tier_dict = pricing_tiers_dict.get(tier) if isinstance(pricing_tiers_dict, dict) else {}
            price = gig_data.get(f"{tier}_tier_price")
            if price is None and isinstance(tier_dict, dict):
                price = tier_dict.get("price")
            if price is not None:
                try:
                    p_clean = float(re.sub(r'[^\d.\-]', '', str(price)))
                    if p_clean < 5.0:
                        issues.append(f"{tier.capitalize()} tier price cannot be less than $5.")
                except Exception:
                    issues.append(f"Invalid price value for {tier} tier: '{price}'.")

            days = gig_data.get(f"{tier}_tier_delivery_days")
            if days is None and isinstance(tier_dict, dict):
                days = tier_dict.get("delivery_days")
            if days is not None:
                try:
                    d_clean = int(re.sub(r'[^\d\-]', '', str(days)))
                    if d_clean < 1:
                        issues.append(f"{tier.capitalize()} tier delivery days must be at least 1.")
                    elif d_clean > 30:
                        issues.append(f"{tier.capitalize()} tier delivery days cannot exceed 30.")
                except Exception:
                    issues.append(f"Invalid delivery days for {tier} tier: '{days}'.")

        return len(issues) == 0, issues

    def validate_proposal(self, proposal_text: str) -> Tuple[bool, List[str]]:
        issues = []
        clean = str(proposal_text or "").strip()
        if not clean:
            issues.append("Proposal text cannot be empty.")
        if len(clean) > 2500:
            issues.append(f"Fiverr Buyer Request / custom offer message is too long ({len(clean)} chars). Recommend under 1500 chars.")
        return len(issues) == 0, issues

    def get_seo_rules(self) -> Dict[str, Any]:
        return {
            "title_max_len": 80,
            "title_optimal_len": 60,
            "max_search_tags": 5,
            "max_tag_length": 20,
            "desc_max_len": 1200,
            "target_keyword_density": 0.02, # 1-2% density in description
            "first_100_chars_must_have_kw": True,
            "package_tiers_count": 3
        }

    def format_gig_markdown(self, gig_data: Dict[str, Any]) -> str:
        title = gig_data.get("title", "")
        tags = gig_data.get("search_tags") or ""
        if isinstance(tags, list):
            tags = ", ".join(str(t) for t in tags)
        desc = gig_data.get("description", "")
        b_name = gig_data.get("basic_tier_name", "Basic")
        b_price = gig_data.get("basic_tier_price", 50)
        b_desc = gig_data.get("basic_tier_desc", "")
        s_name = gig_data.get("standard_tier_name", "Standard")
        s_price = gig_data.get("standard_tier_price", 150)
        s_desc = gig_data.get("standard_tier_desc", "")
        p_name = gig_data.get("premium_tier_name", "Premium")
        p_price = gig_data.get("premium_tier_price", 350)
        p_desc = gig_data.get("premium_tier_desc", "")

        return f"""# {title}

**Search Tags:** `{tags}`

## Description
{desc}

---
## Packages
| Tier | Name | Price | Description |
| :--- | :--- | :--- | :--- |
| Basic | {b_name} | ${b_price} | {b_desc} |
| Standard | {s_name} | ${s_price} | {s_desc} |
| Premium | {p_name} | ${p_price} | {p_desc} |
"""
