from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from core.reach.feed_engine import ReachFeedEngine
from core.platforms.browser_agent import FreelanceBrowserAgent
from core.brain.brain import BrainManager

router = APIRouter()
feed_engine = ReachFeedEngine()
browser_agent = FreelanceBrowserAgent()
brain = BrainManager()

class InspectRequest(BaseModel):
    url: str
    platform: Optional[str] = "fiverr"

class AddFeedPostRequest(BaseModel):
    platform: Optional[str] = "fiverr"
    author_name: Optional[str] = "Prospective Buyer"
    author_headline: Optional[str] = ""
    post_text: str
    post_url: Optional[str] = ""
    budget: Optional[str] = ""
    tags: Optional[str] = ""

class ConnectCookieRequest(BaseModel):
    cookie: str
    platform: Optional[str] = "fiverr"

class ConnectBrowserRequest(BaseModel):
    platform: Optional[str] = "fiverr"

@router.get("/status")
def get_connection_status():
    """Returns real-time account connection status for Fiverr and Upwork."""
    return browser_agent.get_auth_status()

@router.post("/connect-cookie")
def connect_cookie(req: ConnectCookieRequest):
    """Directly attaches session cookie for 1-click platform connection."""
    res = browser_agent.save_cookie(req.cookie, platform=req.platform or "fiverr")
    return res

@router.post("/connect-browser")
def connect_browser(req: ConnectBrowserRequest):
    """Launches interactive browser window to securely log into Fiverr or Upwork."""
    res = browser_agent.launch_interactive_login(platform=req.platform or "fiverr")
    return res

@router.post("/disconnect")
def disconnect_platform(req: ConnectBrowserRequest):
    """Disconnects session cookies for the specified platform."""
    res = browser_agent.disconnect(platform=req.platform or "fiverr")
    return res

@router.get("/feed")
def get_feed(limit: int = 30):
    """Returns scanned jobs and opportunities from the Reach feed."""
    posts = feed_engine.get_recent_scanned_posts(limit=limit)
    return {"posts": posts, "count": len(posts)}

@router.delete("/feed/{post_id}")
def delete_feed_post(post_id: int):
    """Deletes an item from the scanned feed."""
    from core.db.database import get_connection
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("DELETE FROM scanned_feed_posts WHERE id = ?", (post_id,))
        deleted = c.rowcount
        conn.commit()
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Feed post not found")
        return {"status": "deleted", "id": post_id}
    finally:
        conn.close()

@router.post("/feed")
def add_feed_post(req: AddFeedPostRequest):
    """Manually adds or saves a job post or buyer brief into the active Reach feed."""
    post_id = feed_engine.save_feed_post(req.dict())
    return {"status": "success", "id": post_id}

@router.post("/inspect")
def inspect_url(req: InspectRequest):
    """
    Inspects any freelance URL (gig, catalog, or job post) and generates
    a strategic winning angle grounded in the Brain's verified Story Bank.
    """
    clean_url = (req.url or "").strip()
    if not clean_url or clean_url.lower() in ("http://", "https://"):
        raise HTTPException(status_code=400, detail="A valid URL is required for inspection.")

    extracted = feed_engine.inspect_url(clean_url)
    if extracted.get("status") != "success":
        return extracted

    title = extracted.get("title", "Freelance Listing")
    content = extracted.get("content", "")

    # Ground in Brain Story Bank
    strategy = feed_engine.generate_brain_angle(title, content, platform=req.platform or "fiverr")

    # Also automatically save to feed for fast reference
    feed_engine.save_feed_post({
        "platform": req.platform or "fiverr",
        "author_name": title[:40],
        "author_headline": f"Inspected via {extracted.get('backend', 'Reader')}",
        "post_text": strategy.get("executive_summary", content[:300]),
        "post_url": clean_url,
        "budget": "",
        "tags": req.platform or "fiverr"
    })

    return {
        "status": "success",
        "title": title,
        "backend": extracted.get("backend"),
        "content_preview": content[:1500],
        "strategy": strategy
    }
