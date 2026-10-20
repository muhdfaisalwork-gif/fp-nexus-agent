import re
import sqlite3
from typing import Dict, List, Any, Optional
from core.db.database import get_connection

class BrainManager:
    """
    Cognitive Brain & Freelance Story Bank:
    Provides verified metrics, project deliveries, and scars to prevent hallucination.
    """

    def __init__(self):
        pass

    def get_receipts(self, query: str = "", category: str = "", limit: int = 5) -> List[Dict[str, Any]]:
        safe_limit = max(1, int(limit or 5))
        conn = get_connection()
        try:
            cursor = conn.cursor()
            
            sql = "SELECT * FROM story_bank WHERE 1=1"
            params = []

            if category:
                sql += " AND category LIKE ?"
                params.append(f"%{category}%")

            if query:
                # Extract meaningful words (3+ chars) excluding common stopwords
                words = [w.lower() for w in re.findall(r'[a-zA-Z0-9_\-\.]{3,}', query)]
                stop_words = {"with", "that", "this", "have", "from", "your", "want", "looking", "need", "build", "developer", "senior", "client", "project", "will", "some", "good", "fast"}
                keywords = [w for w in words if w not in stop_words][:4]

                if keywords:
                    clauses = []
                    for kw in keywords:
                        clauses.append("(title LIKE ? OR solution_stack LIKE ? OR verified_metrics LIKE ? OR problem LIKE ?)")
                        p = f"%{kw}%"
                        params.extend([p, p, p, p])
                    sql += f" AND ({' OR '.join(clauses)})"
                else:
                    p_query = f"%{query[:30].strip()}%"
                    sql += " AND (title LIKE ? OR solution_stack LIKE ? OR verified_metrics LIKE ? OR problem LIKE ?)"
                    params.extend([p_query, p_query, p_query, p_query])

            sql += " ORDER BY id DESC LIMIT ?"
            params.append(safe_limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            # If specific keyword matching produced no rows, fallback to general receipts
            if not rows and query:
                cursor.execute("SELECT * FROM story_bank ORDER BY id DESC LIMIT ?", (safe_limit,))
                rows = cursor.fetchall()

            results = []
            for r in rows:
                results.append({
                    "id": r["id"],
                    "category": r["category"],
                    "title": r["title"],
                    "client_niche": r["client_niche"],
                    "problem": r["problem"],
                    "solution_stack": r["solution_stack"],
                    "verified_metrics": r["verified_metrics"],
                    "duration_days": r["duration_days"],
                    "deliverables": r["deliverables"],
                    "created_at": r["created_at"]
                })
            return results
        finally:
            conn.close()

    def add_receipt(
        self,
        category: str,
        title: str,
        client_niche: str,
        problem: str,
        solution_stack: str,
        verified_metrics: str,
        duration_days: int = 7,
        deliverables: str = ""
    ) -> int:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO story_bank (
                    category, title, client_niche, problem, solution_stack,
                    verified_metrics, duration_days, deliverables
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (category, title, client_niche, problem, solution_stack, verified_metrics, duration_days, deliverables))
            receipt_id = cursor.lastrowid
            conn.commit()
            return receipt_id
        finally:
            conn.close()

    def format_receipts_for_prompt(self, receipts: List[Dict[str, Any]]) -> str:
        """Formats receipts into compact, factual ground truth for the LLM prompt."""
        if not receipts:
            return "No specific case studies found. Stick to general verified engineering practices; never invent fake client statistics."
        
        lines = ["VERIFIED FREELANCE RECEIPTS & PAST CASE STUDIES (CITE THESE NUMBERS):"]
        for i, r in enumerate(receipts, 1):
            lines.append(
                f"{i}. Project: {r['title']} ({r['client_niche']})\n"
                f"   Problem: {r['problem']}\n"
                f"   Stack: {r['solution_stack']}\n"
                f"   Measured Result: {r['verified_metrics']}\n"
                f"   Deliverables: {r['deliverables']}"
            )
        return "\n".join(lines)
