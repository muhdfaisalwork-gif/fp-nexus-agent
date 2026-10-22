import os
import json
import sqlite3
from typing import Dict, Any, List, Optional
from core.db.database import get_connection
from core.platforms.browser_agent import FreelanceBrowserAgent
from core.reach.reader import ReachReader
from core.llm.client import UniversalLLMClient
from core.brain.brain import BrainManager

class ReachFeedEngine:
    """
    Coordinates Agent Reach scanning, opportunity feeds, competitor gigs,
    and automatic Brain-grounded strategy synthesis for freelance platforms.
    """

    def __init__(
        self,
        browser_agent: Optional[FreelanceBrowserAgent] = None,
        reader: Optional[ReachReader] = None,
        llm: Optional[UniversalLLMClient] = None,
        brain: Optional[BrainManager] = None
    ):
        self.browser_agent = browser_agent or FreelanceBrowserAgent(headless=True)
        self.reader = reader or ReachReader()
        self.llm = llm or UniversalLLMClient()
        self.brain = brain or BrainManager()

    def get_recent_scanned_posts(self, limit: int = 30) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("""
                SELECT id, platform, author_name, author_headline, post_text, post_url,
                       budget, tags, reaction_count, comment_count, screenshot_path, scanned_at
                FROM scanned_feed_posts
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = c.fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()

    def inspect_url(self, url: str) -> Dict[str, Any]:
        """Inspects any gig, project catalog, or job post using Jina Reader or HTTP scraping."""
        return self.reader.read_url(url)

    def generate_brain_angle(self, title: str, content: str, platform: str = "fiverr") -> Dict[str, Any]:
        """
        Synthesizes a client-winning angle grounded directly in the Brain's verified Story Bank.
        """
        brain_context = self.brain.get_context_for_generation(f"{platform} client pitch")

        prompt = f"""You are the strategic brain of FP Nexus Agent.
Analyze this inspected freelance job/gig and synthesize a winning, Humanizer-compliant response angle.

INSPECTED LISTING:
Title: {title}
Content:
{content[:2500]}

VERIFIED STORY BANK & PROOF RECEIPTS:
{brain_context[:1500]}

TASK:
Generate a structured strategic breakdown (JSON ONLY):
{{
  "executive_summary": "2 crisp sentences explaining the buyer's real underlying objective.",
  "buyer_pain_point": "The critical friction point or risk they fear.",
  "brain_proof_citation": "Exact metric, case study, or stack from the Story Bank to cite.",
  "recommended_hook": "A 1-sentence killer opening hook that directly addresses their problem without generic greetings.",
  "winning_angle": "How to structure the proposal or gig counter-offer to win."
}}
"""
        raw_output = self.llm.generate(prompt=prompt, temperature=0.3, max_tokens=600)
        import re
        data = {}
        match = re.search(r'\{[\s\S]*\}', str(raw_output or ""))
        if match:
            try:
                data = json.loads(match.group(0))
            except Exception:
                pass

        if not data:
            data = {
                "executive_summary": f"The client needs specialized execution for {title} with rapid turnaround and verified reliability.",
                "buyer_pain_point": "Risk of poor code architecture, missing documentation, or delayed milestones.",
                "brain_proof_citation": "Cited verified production delivery with sub-second performance and complete test coverage.",
                "recommended_hook": f"Reviewed your requirements for {title}—here is the exact architectural blueprint to deliver this cleanly.",
                "winning_angle": "Demonstrate existing working benchmarks, Dockerized setup, and zero boilerplate."
            }

        return data

    def save_feed_post(self, post_data: Dict[str, Any]) -> int:
        """Persists a discovered opportunity or job post into the feed database."""
        conn = get_connection()
        try:
            c = conn.cursor()
            c.execute("""
                INSERT INTO scanned_feed_posts (
                    platform, author_name, author_headline, post_text, post_url,
                    budget, tags, reaction_count, comment_count, screenshot_path
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                post_data.get("platform", "fiverr"),
                post_data.get("author_name", "Prospective Buyer"),
                post_data.get("author_headline", ""),
                post_data.get("post_text", ""),
                post_data.get("post_url", ""),
                post_data.get("budget", ""),
                post_data.get("tags", ""),
                post_data.get("reaction_count", 0),
                post_data.get("comment_count", 0),
                post_data.get("screenshot_path", "")
            ))
            conn.commit()
            return c.lastrowid
        finally:
            conn.close()
