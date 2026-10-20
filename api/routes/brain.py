from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.brain.brain import BrainManager
from core.db.database import get_connection

router = APIRouter()
brain = BrainManager()

class AddReceiptRequest(BaseModel):
    category: str
    title: str
    client_niche: str
    problem: str
    solution_stack: str
    verified_metrics: str
    duration_days: Optional[int] = 7
    deliverables: Optional[str] = ""

@router.get("/receipts")
def list_receipts(query: Optional[str] = "", category: Optional[str] = ""):
    receipts = brain.get_receipts(query=query or "", category=category or "", limit=100)
    return {"receipts": receipts}

@router.post("/receipts")
def add_receipt(req: AddReceiptRequest):
    receipt_id = brain.add_receipt(
        category=req.category,
        title=req.title,
        client_niche=req.client_niche,
        problem=req.problem,
        solution_stack=req.solution_stack,
        verified_metrics=req.verified_metrics,
        duration_days=req.duration_days or 7,
        deliverables=req.deliverables or ""
    )
    return {"status": "created", "receipt_id": receipt_id}

@router.delete("/receipts/{receipt_id}")
def delete_receipt(receipt_id: int):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM story_bank WHERE id = ?", (receipt_id,))
        deleted = c.rowcount
        conn.commit()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Receipt not found")
        return {"status": "deleted", "receipt_id": receipt_id}
    finally:
        conn.close()

