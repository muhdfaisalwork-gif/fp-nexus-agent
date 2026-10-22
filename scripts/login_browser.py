#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Interactive Browser Login Helper for FP Nexus Agent
Opens a headed Chromium window for Fiverr or Upwork to capture authenticated session cookies.

Usage:
    python scripts/login_browser.py fiverr
    python scripts/login_browser.py upwork
"""

import sys
import os

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.platforms.browser_agent import FreelanceBrowserAgent

def main():
    platform = "fiverr"
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("upwork", "freelancer"):
        platform = sys.argv[1].lower()

    print("=" * 65)
    print(f"   ⚡ FP NEXUS - Interactive Browser Login ({platform.upper()})")
    print("=" * 65)
    print(f"► Launching clean browser window for {platform.capitalize()}...")
    print("► Please log in with your credentials or 2FA.")
    print("► When login completes, session cookies will be saved automatically.\n")

    agent = FreelanceBrowserAgent(headless=False)
    res = agent.launch_interactive_login(platform=platform)

    print("\n" + "=" * 65)
    print("Status:", res.get("status"))
    print("Message:", res.get("message"))
    print("=" * 65)

if __name__ == "__main__":
    main()
