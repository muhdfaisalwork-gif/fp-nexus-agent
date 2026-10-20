from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core.db.database import get_connection
from core.skills.inbox_handler import InboxHandler

router = APIRouter()
handler = InboxHandler()


class ReplyRequest(BaseModel):
    client_message: str
    conversation_context: Optional[str] = ""
    gig_or_project_name: Optional[str] = ""
    freelancer_rate: Optional[float] = 50.0
    client_name: Optional[str] = "Buyer"
    platform: Optional[str] = "fiverr"

@router.get("/history")
def list_inbox_history():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM inbox_conversations ORDER BY id DESC LIMIT 50")
        rows = c.fetchall()

        items = []
        for r in rows:
            items.append({
                "id": r["id"],
                "platform": r["platform"],
                "client_name": r["client_name"],
                "project_topic": r["project_topic"],
                "last_client_message": r["last_client_message"],
                "detected_intent": r["detected_intent"],
                "drafted_reply": r["drafted_reply"],
                "status": r["status"],
                "created_at": r["created_at"]
            })
        return {"conversations": items}
    finally:
        conn.close()

@router.post("/reply")
def draft_reply(req: ReplyRequest):
    result = handler.reply_to_client(
        client_message=req.client_message,
        conversation_context=req.conversation_context or "",
        gig_or_project_name=req.gig_or_project_name or "",
        freelancer_rate=req.freelancer_rate or 50.0
    )

    # Save to history
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute('''
            INSERT INTO inbox_conversations (
                platform, client_name, project_topic, last_client_message,
                detected_intent, drafted_reply, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            req.platform or "fiverr",
            req.client_name or "Buyer",
            req.gig_or_project_name or "",
            req.client_message,
            result.get("detected_intent", "general"),
            result.get("reply_text", ""),
            "draft"
        ))
        conv_id = c.lastrowid
        conn.commit()
    finally:
        conn.close()

    result["conversation_id"] = conv_id
    return result

@router.delete("/{conv_id}")
def delete_inbox_conversation(conv_id: int):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM inbox_conversations WHERE id = ?", (conv_id,))
        deleted = c.rowcount
        conn.commit()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return {"status": "deleted", "conversation_id": conv_id}
    finally:
        conn.close()

