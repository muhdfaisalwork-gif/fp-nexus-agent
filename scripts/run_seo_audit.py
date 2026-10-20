#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
CLI runner for FP Nexus Agent Weekly / Bi-Weekly SEO Audits.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.db.database import init_db
from core.scheduler.seo_cron import SEOScheduler
from core.seo.platform_seo import PlatformSEO

def main():
    print("=" * 60)
    print("  FP Nexus Agent - Algorithmic SEO Audit Runner")
    print("=" * 60)
    init_db()

    scheduler = SEOScheduler()
    results = scheduler.check_and_run_scheduled_audits()

    if not results:
        print("\nAll active gigs are currently fresh (< 7 days since last optimization).")
        print("To run a manual audit, use the Web Studio Dashboard at http://localhost:8001/seo")
    else:
        print(f"\nCompleted audits for {len(results)} gigs:")
        for r in results:
            print(f"- Gig #{r['gig_id']} ({r['gig_title']}) -> Action: {r['action']}")
            if "recommended_tags" in r:
                rec_tags = r['recommended_tags']
                tags_str = ", ".join(rec_tags) if isinstance(rec_tags, list) else str(rec_tags)
                print(f"  Recommended Tags: {tags_str}")

    print("\nAudit run complete.")

if __name__ == "__main__":
    main()
