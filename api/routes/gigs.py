from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any, Union
import json
from datetime import datetime

from core.db.database import get_connection
from core.skills.gig_optimizer import GigOptimizer
from core.seo.platform_seo import PlatformSEO

router = APIRouter()
gig_opt = GigOptimizer()
seo_engine = PlatformSEO()

class OptimizeGigRequest(BaseModel):
    topic: str
    target_keywords: Optional[List[str]] = None
    platform: str = "fiverr"
    category: str = "Programming & Tech"
    custom_instructions: Optional[str] = ""

class SaveGigRequest(BaseModel):
    platform: Optional[str] = "fiverr"
    title: str
    category: Optional[str] = "Programming & Tech"
    subcategory: Optional[str] = ""
    search_tags: Union[List[str], str] = []
    description: str
    basic_tier_name: Optional[str] = "Starter"
    basic_tier_desc: Optional[str] = "Core setup"
    basic_tier_price: Optional[float] = 50.0
    basic_tier_delivery_days: Optional[int] = 2
    standard_tier_name: Optional[str] = "Standard"
    standard_tier_desc: Optional[str] = "Full features & tests"
    standard_tier_price: Optional[float] = 150.0
    standard_tier_delivery_days: Optional[int] = 4
    premium_tier_name: Optional[str] = "Enterprise"
    premium_tier_desc: Optional[str] = "Production deployment"
    premium_tier_price: Optional[float] = 350.0
    premium_tier_delivery_days: Optional[int] = 7
    faqs: Optional[List[Dict[str, str]]] = []
    requirements: Optional[str] = ""
    seo_score: Optional[float] = 0.0
    flesch_score: Optional[float] = 70.0

@router.get("/")
def list_gigs():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM gigs ORDER BY id DESC")
        rows = c.fetchall()

        gigs = []
        for r in rows:
            tags_raw = r["search_tags"]
            tags = []
            if tags_raw:
                try:
                    if str(tags_raw).strip().startswith("["):
                        tags = json.loads(tags_raw)
                    else:
                        tags = [t.strip() for t in str(tags_raw).split(",") if t.strip()]
                except Exception:
                    tags = []
            if not isinstance(tags, list):
                tags = []

            faqs_raw = r["faqs"]
            faqs = []
            if faqs_raw:
                try:
                    faqs = json.loads(faqs_raw)
                except Exception:
                    faqs = []
            if not isinstance(faqs, list):
                faqs = []

            gigs.append({
                "id": r["id"],
                "platform": r["platform"],
                "title": r["title"],
                "category": r["category"],
                "subcategory": r["subcategory"],
                "search_tags": tags,
                "description": r["description"],
                "basic_tier_name": r["basic_tier_name"],
                "basic_tier_desc": r["basic_tier_desc"],
                "basic_tier_price": r["basic_tier_price"],
                "basic_tier_delivery_days": r["basic_tier_delivery_days"],
                "standard_tier_name": r["standard_tier_name"],
                "standard_tier_desc": r["standard_tier_desc"],
                "standard_tier_price": r["standard_tier_price"],
                "standard_tier_delivery_days": r["standard_tier_delivery_days"],
                "premium_tier_name": r["premium_tier_name"],
                "premium_tier_desc": r["premium_tier_desc"],
                "premium_tier_price": r["premium_tier_price"],
                "premium_tier_delivery_days": r["premium_tier_delivery_days"],
                "faqs": faqs,
                "requirements": r["requirements"] or "",
                "seo_score": r["seo_score"] or 0.0,
                "flesch_score": r["flesch_score"] or 70.0,
                "last_optimized_at": r["last_optimized_at"],
                "created_at": r["created_at"]
            })
        return {"gigs": gigs}
    finally:
        conn.close()

@router.post("/optimize")
def optimize_gig(req: OptimizeGigRequest):
    result = gig_opt.optimize_gig(
        topic=req.topic,
        target_keywords=req.target_keywords,
        platform_name=req.platform,
        category=req.category,
        custom_instructions=req.custom_instructions or ""
    )
    # Calculate SEO score on the generated gig
    audit = seo_engine.audit_gig_seo(result)
    result["seo_audit"] = audit
    result["seo_score"] = audit.get("seo_score", 85.0)
    return result

@router.post("/save")
def save_gig(req: SaveGigRequest):
    tags = req.search_tags
    if isinstance(tags, str):
        tags_str = tags.strip()
        if tags_str.startswith("["):
            try:
                tags = json.loads(tags_str)
            except Exception:
                tags = [t.strip() for t in tags_str.split(",") if t.strip()]
        else:
            tags = [t.strip() for t in tags_str.split(",") if t.strip()]
    if not isinstance(tags, list):
        tags = []

    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            INSERT INTO gigs (
                platform, title, category, subcategory, search_tags, description,
                basic_tier_name, basic_tier_desc, basic_tier_price, basic_tier_delivery_days,
                standard_tier_name, standard_tier_desc, standard_tier_price, standard_tier_delivery_days,
                premium_tier_name, premium_tier_desc, premium_tier_price, premium_tier_delivery_days,
                faqs, requirements, seo_score, flesch_score, last_optimized_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            req.platform, req.title, req.category, req.subcategory,
            json.dumps(tags), req.description,
            req.basic_tier_name, req.basic_tier_desc, req.basic_tier_price, req.basic_tier_delivery_days,
            req.standard_tier_name, req.standard_tier_desc, req.standard_tier_price, req.standard_tier_delivery_days,
            req.premium_tier_name, req.premium_tier_desc, req.premium_tier_price, req.premium_tier_delivery_days,
            json.dumps(req.faqs), req.requirements, req.seo_score, req.flesch_score
        ))
        gig_id = c.lastrowid
        conn.commit()
        return {"status": "saved", "gig_id": gig_id}
    finally:
        conn.close()

@router.delete("/{gig_id}")
def delete_gig(gig_id: int):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM gigs WHERE id = ?", (gig_id,))
        deleted = c.rowcount
        conn.commit()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Gig not found")
        return {"status": "deleted", "gig_id": gig_id}
    finally:
        conn.close()


@router.post("/{gig_id}/audit")
def audit_saved_gig(gig_id: int):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM gigs WHERE id = ?", (gig_id,))
        row = c.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Gig not found")

        tags_raw = row["search_tags"]
        tags = []
        if tags_raw:
            try:
                if str(tags_raw).strip().startswith("["):
                    tags = json.loads(tags_raw)
                else:
                    tags = [t.strip() for t in str(tags_raw).split(",") if t.strip()]
            except Exception:
                tags = []
        if not isinstance(tags, list):
            tags = []

        gig_data = {
            "title": row["title"],
            "description": row["description"],
            "search_tags": tags,
            "category": row["category"]
        }
        audit = seo_engine.audit_gig_seo(gig_data)
        # Update score in db
        c.execute("UPDATE gigs SET seo_score = ? WHERE id = ?", (audit["seo_score"], gig_id))
        # Record audit in history
        c.execute('''
            INSERT INTO seo_audits (
                gig_id, audit_type, previous_tags, recommended_tags, score, recommendations, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            gig_id,
            "manual_dashboard_audit",
            ", ".join(str(t) for t in tags),
            ", ".join(str(t) for t in tags),
            audit["seo_score"],
            json.dumps(audit["recommendations"]),
            "reviewed"
        ))
        conn.commit()
        return audit
    finally:
        conn.close()
