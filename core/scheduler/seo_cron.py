import time
import json
import threading
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from core.db.database import get_connection
from core.seo.platform_seo import PlatformSEO

class SEOScheduler:
    """
    Automated Weekly / Bi-Weekly Freelance Platform SEO Scheduler:
    - Weekly: Detects gigs needing keyword/tag refresh (>= 7 days).
    - Bi-Weekly: Runs full deep scan (>= 14 days) and records audit reports in database.
    """

    def __init__(self, platform_seo: Optional[PlatformSEO] = None):
        self.seo = platform_seo or PlatformSEO()
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()

    @staticmethod
    def parse_timestamp(ts_str: Optional[str]) -> Optional[datetime]:
        if not ts_str:
            return None
        clean_str = str(ts_str).replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(clean_str).replace(tzinfo=None)
        except Exception:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
                try:
                    return datetime.strptime(str(ts_str).split(".")[0], fmt.split(".")[0])
                except Exception:
                    continue
        return None

    @staticmethod
    def parse_tags(tags_raw: Any) -> List[str]:
        if not tags_raw:
            return []
        try:
            if str(tags_raw).strip().startswith("["):
                res = json.loads(tags_raw)
                return res if isinstance(res, list) else []
            else:
                return [t.strip() for t in str(tags_raw).split(",") if t.strip()]
        except Exception:
            return []

    @classmethod
    def is_audit_due(cls, ts_str: Optional[str], interval_days: int = 7) -> bool:
        dt = cls.parse_timestamp(ts_str)
        if not dt:
            return True
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        return (now - dt).total_seconds() >= interval_days * 86400

    def check_and_run_scheduled_audits(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM gigs WHERE status = 'active'")
            gigs = cursor.fetchall()

            results = []
            now = datetime.now(timezone.utc).replace(tzinfo=None)

            for g in gigs:
                gig_id = g["id"]
                last_opt_str = g["last_optimized_at"] or g["created_at"]
                last_opt_dt = self.parse_timestamp(last_opt_str)
                if not last_opt_dt:
                    last_opt_dt = now - timedelta(days=15)

                days_since = (now - last_opt_dt).days
                tags = self.parse_tags(g["search_tags"])

                gig_data = {
                    "id": gig_id,
                    "title": g["title"],
                    "category": g["category"],
                    "description": g["description"],
                    "search_tags": tags
                }

                if days_since >= 14:
                    # Run Bi-Weekly Deep Scan
                    audit = self.seo.biweekly_deep_scan(gig_data)
                    cursor.execute('''
                        INSERT INTO seo_audits (
                            gig_id, audit_type, previous_tags, recommended_tags,
                            score, recommendations, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        gig_id,
                        "biweekly_deep_scan",
                        ", ".join(str(t) for t in tags),
                        ", ".join(str(t) for t in audit["recommended_tags"]) if isinstance(audit.get("recommended_tags"), list) else str(audit.get("recommended_tags", "")),
                        audit.get("current_seo_score", 0.0),
                        json.dumps(audit.get("recommendations", [])),
                        "pending_review"
                    ))
                    # Update last_optimized_at in gigs table to prevent duplicate continuous auditing
                    cursor.execute('''
                        UPDATE gigs SET last_optimized_at = CURRENT_TIMESTAMP, seo_score = ? WHERE id = ?
                    ''', (audit.get("current_seo_score", 0.0), gig_id))

                    results.append({
                        "gig_id": gig_id,
                        "gig_title": g["title"],
                        "action": "biweekly_deep_scan",
                        "score": audit.get("current_seo_score", 0.0),
                        "recommended_tags": audit.get("recommended_tags", [])
                    })
                elif days_since >= 7:
                    # Run Weekly Tag Refresh
                    refresh = self.seo.weekly_keyword_refresh(
                        current_tags=tags,
                        gig_title=g["title"],
                        gig_category=g["category"]
                    )
                    rec_tags = refresh.get("recommended_tags", [])
                    cursor.execute('''
                        INSERT INTO seo_audits (
                            gig_id, audit_type, previous_tags, recommended_tags,
                            score, recommendations, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        gig_id,
                        "weekly_keyword_refresh",
                        ", ".join(str(t) for t in tags),
                        ", ".join(str(t) for t in rec_tags) if isinstance(rec_tags, list) else str(rec_tags),
                        g["seo_score"] or 0.0,
                        json.dumps([refresh.get("rationale", "Weekly keyword refresh")]),
                        "pending_review"
                    ))
                    # Update last_optimized_at in gigs table
                    cursor.execute('''
                        UPDATE gigs SET last_optimized_at = CURRENT_TIMESTAMP WHERE id = ?
                    ''', (gig_id,))

                    results.append({
                        "gig_id": gig_id,
                        "gig_title": g["title"],
                        "action": "weekly_keyword_refresh",
                        "previous_tags": tags,
                        "recommended_tags": rec_tags
                    })

            conn.commit()
            return results
        finally:
            conn.close()

    def start_background_loop(self, check_interval_hours: int = 12):
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        def _loop():
            while self._running and not self._stop_event.is_set():
                try:
                    self.check_and_run_scheduled_audits()
                except Exception as e:
                    print(f"[SEOScheduler] Error during audit loop: {e}")
                if self._stop_event.wait(timeout=check_interval_hours * 3600):
                    break

        self._thread = threading.Thread(target=_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()
