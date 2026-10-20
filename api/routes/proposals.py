from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from core.db.database import get_connection
from core.skills.proposal_writer import ProposalWriter
from core.skills.client_outreach import ClientOutreach

router = APIRouter()
writer = ProposalWriter()
outreach = ClientOutreach()


class GenerateProposalRequest(BaseModel):
    job_description: str
    client_budget: Optional[str] = None
    platform: str = "upwork"
    hook_angle: Optional[str] = "solution_first"
    specific_stack_or_approach: Optional[str] = ""

class DraftOutreachRequest(BaseModel):
    prospect_name_or_company: str
    prospect_problem_or_tech: str
    outreach_channel: Optional[str] = "direct_message"
    specific_observation: Optional[str] = ""

class SaveProposalRequest(BaseModel):
    platform: str = "upwork"
    job_title: Optional[str] = "Client Job"
    job_description: str
    client_budget: Optional[str] = None
    proposal_text: str
    humanizer_score: Optional[float] = 100.0

@router.get("/")
def list_proposals():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM proposals ORDER BY id DESC LIMIT 50")
        rows = c.fetchall()

        proposals = []
        for r in rows:
            proposals.append({
                "id": r["id"],
                "platform": r["platform"],
                "job_title": r["job_title"],
                "job_description": r["job_description"],
                "client_budget": r["client_budget"],
                "proposal_text": r["proposal_text"],
                "humanizer_score": r["humanizer_score"],
                "status": r["status"],
                "created_at": r["created_at"]
            })
        return {"proposals": proposals}
    finally:
        conn.close()

@router.post("/generate")
def generate_proposal(req: GenerateProposalRequest):
    result = writer.draft_proposal(
        job_description=req.job_description,
        client_budget=req.client_budget,
        platform_name=req.platform,
        hook_angle=req.hook_angle or "solution_first",
        specific_stack_or_approach=req.specific_stack_or_approach or ""
    )
    return result

@router.post("/outreach")
def generate_outreach(req: DraftOutreachRequest):
    return outreach.draft_outreach(
        prospect_name_or_company=req.prospect_name_or_company,
        prospect_problem_or_tech=req.prospect_problem_or_tech,
        outreach_channel=req.outreach_channel or "direct_message",
        specific_observation=req.specific_observation or ""
    )

@router.post("/save")
def save_proposal(req: SaveProposalRequest):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            INSERT INTO proposals (
                platform, job_title, job_description, client_budget, proposal_text, humanizer_score
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (req.platform, req.job_title, req.job_description, req.client_budget, req.proposal_text, req.humanizer_score))
        prop_id = c.lastrowid
        conn.commit()
        return {"status": "saved", "proposal_id": prop_id}
    finally:
        conn.close()

@router.delete("/{proposal_id}")
def delete_proposal(proposal_id: int):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM proposals WHERE id = ?", (proposal_id,))
        deleted = c.rowcount
        conn.commit()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Proposal not found")
        return {"status": "deleted", "proposal_id": proposal_id}
    finally:
        conn.close()

