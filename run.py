#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FP Nexus Agent - Main Runner Entrypoint
Starts the FastAPI Studio Dashboard (:8001) and initializes background SEO scheduler.
"""

import os
import sys
import uvicorn
from dotenv import load_dotenv

load_dotenv()

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db.database import init_db
from core.scheduler.seo_cron import SEOScheduler
from core.llm.client import UniversalLLMClient

def print_banner(host: str, port: int, client: UniversalLLMClient):
    print("=" * 65)
    print("   ⚡ FP NEXUS AGENT — Autonomous Freelancing Platforms Studio")
    print("   Fiverr • Upwork • Freelancer • Contra • 82-Rule Humanizer")
    print("=" * 65)
    print(f"   ► Dashboard UI:      http://localhost:{port}")
    print(f"   ► MCP Stdio Server:  python run_mcp.py")
    print(f"   ► Active Provider:   {client.active_provider_name.upper()}")
    print(f"   ► Active Model:      {client.current_model}")
    print(f"   ► SEO Scheduler:     Active (Weekly tags + 14-day deep scan)")
    print(f"   ► 82 Rules:          STRICT ENFORCEMENT ON")
    print("=" * 65)
    print("   Press Ctrl+C to stop the agent server.\n")

def main():
    # 1. Initialize SQLite Database
    init_db()

    # 2. Start Background SEO Scheduler Loop
    scheduler = SEOScheduler()
    scheduler.start_background_loop(check_interval_hours=12)

    # 3. Detect Host and Port
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8001"))

    # 4. Print Banner
    client = UniversalLLMClient()
    print_banner(host, port, client)

    # 5. Launch FastAPI via Uvicorn
    uvicorn.run("api.app:app", host=host, port=port, reload=False, log_level="info")

if __name__ == "__main__":
    main()
