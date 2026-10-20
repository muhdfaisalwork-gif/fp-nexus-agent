from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.db.database import get_connection
from core.reach.scanner import CompetitorScanner

router = APIRouter()
scanner = CompetitorScanner()

class ScanCompetitorRequest(BaseModel):
    url: str
    platform: Optional[str] = "fiverr"

@router.get("/")
def list_competitor_scans():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM competitor_scans ORDER BY id DESC LIMIT 50")
        rows = c.fetchall()

        scans = []
        for r in rows:
            scans.append({
                "id": r["id"],
                "platform": r["platform"],
                "url": r["url"],
                "competitor_name": r["competitor_name"],
                "gig_title": r["gig_title"],
                "price_range": r["price_range"],
                "extracted_tags": r["extracted_tags"],
                "review_count": r["review_count"],
                "rating": r["rating"],
                "key_takeaways": r["key_takeaways"],
                "counter_strategy": r["counter_strategy"],
                "scanned_at": r["scanned_at"]
            })
        return {"scans": scans}
    finally:
        conn.close()

@router.post("/scan")
def scan_competitor(req: ScanCompetitorRequest):
    result = scanner.scan_competitor_url(url=req.url, platform_name=req.platform or "fiverr")
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message", "Failed to scan competitor URL"))
    return result

@router.delete("/{scan_id}")
def delete_competitor_scan(scan_id: int):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM competitor_scans WHERE id = ?", (scan_id,))
        deleted = c.rowcount
        conn.commit()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Competitor scan not found")
        return {"status": "success", "deleted_id": scan_id}
    finally:
        conn.close()

