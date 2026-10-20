from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Union
import json

from core.db.database import get_connection
from core.seo.platform_seo import PlatformSEO
from core.scheduler.seo_cron import SEOScheduler

router = APIRouter()
seo_engine = PlatformSEO()
scheduler = SEOScheduler(seo_engine)

class WeeklyRefreshRequest(BaseModel):
    current_tags: Union[List[str], str] = []
    gig_title: str
    gig_category: Optional[str] = "Programming & Tech"

@router.get("/audits")
def list_seo_audits():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            SELECT a.*, g.title as gig_title, g.platform as platform
            FROM seo_audits a
            LEFT JOIN gigs g ON a.gig_id = g.id
            ORDER BY a.id DESC LIMIT 50
        ''')
        rows = c.fetchall()
    finally:
        conn.close()

    audits = []
    for r in rows:
        recs = []
        try:
            recs = json.loads(r["recommendations"]) if r["recommendations"] else []
        except Exception:
            recs = [r["recommendations"]]

        audits.append({
            "id": r["id"],
            "gig_id": r["gig_id"],
            "gig_title": r["gig_title"] or "Standalone Audit",
            "platform": r["platform"] or "fiverr",
            "audit_type": r["audit_type"],
            "previous_tags": r["previous_tags"],
            "recommended_tags": r["recommended_tags"],
            "score": r["score"],
            "recommendations": recs,
            "status": r["status"],
            "created_at": r["created_at"]
        })
    return {"audits": audits}

@router.post("/run-scheduled")
def run_scheduled_audits():
    results = scheduler.check_and_run_scheduled_audits()
    return {"status": "success", "processed_count": len(results), "results": results}

@router.post("/weekly-refresh")
def refresh_tags(req: WeeklyRefreshRequest):
    return seo_engine.weekly_keyword_refresh(
        current_tags=req.current_tags,
        gig_title=req.gig_title,
        gig_category=req.gig_category
    )

@router.delete("/audits/{audit_id}")
def delete_seo_audit(audit_id: int):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM seo_audits WHERE id = ?", (audit_id,))
        deleted = c.rowcount
        conn.commit()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Audit not found")
        return {"status": "deleted", "audit_id": audit_id}
    finally:
        conn.close()
