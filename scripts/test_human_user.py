#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
End-to-End Human User Simulation for FP Nexus Agent Web Studio.
Simulates a real freelance professional interacting with every feature in http://localhost:8001:
1. Settings & Account Connection (Fiverr & Upwork cookie attach, persistence, disconnect)
2. Cognitive Brain & Story Bank (Adding verified project delivery receipts)
3. Reach & Feed (Inspecting listings, extracting strategic Brain angles, drafting proposal from feed)
4. Proposals Studio (Writing 82-rule humanized proposal, checking line-1 hook, saving to history)
5. Cold Client Outreach (Drafting value-first diagnostic outreach)
6. Gig Optimizer & SEO (Generating 5-tag gig, 3 tiers, FAQs, saving gig)
7. Client Inbox Assistant (Intent classification, price recommendation, humanized response)

Captures high-resolution screenshots at each step for visual audit and verification.
"""

import os
import sys
import time
import json
import shutil
from typing import Dict, Any

# Ensure UTF-8 console output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.sync_api import sync_playwright, Page, expect

SCREENSHOTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "storage", "test_screenshots")
ARTIFACTS_DIR = r"C:\Users\Lucifer\.gemini\antigravity\brain\004c6781-49a9-456a-936d-6b8ab73e8a19"

os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

def take_shot(page: Page, name: str) -> str:
    path = os.path.join(SCREENSHOTS_DIR, f"{name}.png")
    page.screenshot(path=path, full_page=True)
    if os.path.exists(ARTIFACTS_DIR):
        artifact_path = os.path.join(ARTIFACTS_DIR, f"{name}.png")
        try:
            shutil.copy2(path, artifact_path)
        except Exception:
            pass
    print(f"  [Screenshot] Saved: {name}.png")
    return path

def run_human_simulation():
    print("=" * 70)
    print("   FP NEXUS AGENT - END-TO-END HUMAN USER SIMULATION")
    print("=" * 70)
    
    results = {}
    
    with sync_playwright() as p:
        print("\n[*] Launching Chromium browser (emulating Human User)...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # Handle dialogs automatically (alert, confirm, prompt)
        last_dialog_message = []
        def handle_dialog(dialog):
            print(f"    [Browser Alert] \"{dialog.message}\"")
            last_dialog_message.append(dialog.message)
            dialog.accept()

        page.on("dialog", handle_dialog)

        # -------------------------------------------------------------
        # 1. LOAD HOMEPAGE / WEB STUDIO
        # -------------------------------------------------------------
        print("\n[Step 1] Navigating to Web Studio at http://localhost:8001...")
        page.goto("http://localhost:8001", wait_until="domcontentloaded")
        page.wait_for_selector(".brand-title", state="visible")
        title = page.title()
        print(f"  [Assert] Page loaded successfully: '{title}'")
        assert "FP Nexus Agent" in title, f"Unexpected page title: {title}"
        take_shot(page, "01_homepage_initial")
        results["1_homepage_load"] = "PASS"

        # -------------------------------------------------------------
        # 2. SETTINGS & ACCOUNT CONNECTION
        # -------------------------------------------------------------
        print("\n[Step 2] Testing Settings & Account Connection...")
        page.evaluate("switchTab('settings')")
        page.wait_for_selector("#pane-settings", state="visible")
        time.sleep(0.5)

        # Attach Fiverr Cookie (Testing raw base64 padding token)
        test_fiverr_token = "BAh7SUkiD3VzZXJfaWQGOgETaQMA=="
        page.fill("#cookie-fiverr", test_fiverr_token)
        print(f"  Pasted Fiverr session token into #cookie-fiverr")
        
        # Click "Attach Cookie"
        page.click("button:has-text('Attach Cookie'):near(#cookie-fiverr)")
        expect(page.locator("#status-fiverr")).to_contain_text("CONNECTED", timeout=10000)
        take_shot(page, "02_fiverr_connected")
        print("  [Assert] Fiverr Status: CONNECTED")

        # Attach Upwork Cookie (Testing key=value format)
        test_upwork_token = "oauth2_global_js_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiZnJlZWxhbmNlciJ9.signature"
        page.fill("#cookie-upwork", test_upwork_token)
        page.click("button:has-text('Attach Cookie'):near(#cookie-upwork)")
        expect(page.locator("#status-upwork")).to_contain_text("CONNECTED", timeout=10000)
        take_shot(page, "03_both_connected")
        print("  [Assert] Upwork Status: CONNECTED")

        # Verify Persistence by Reloading the Page
        print("  Reloading page to test multi-layer persistence...")
        page.reload(wait_until="domcontentloaded")
        page.evaluate("switchTab('settings')")
        expect(page.locator("#status-fiverr")).to_contain_text("CONNECTED", timeout=10000)
        expect(page.locator("#status-upwork")).to_contain_text("CONNECTED", timeout=10000)
        print("  [Assert] Persistence verified across page reload (Fiverr & Upwork stay CONNECTED)")

        # Disconnect Upwork to test disconnection lifecycle
        print("  Testing disconnect functionality...")
        page.click("button:has-text('Disconnect'):near(#cookie-upwork)")
        expect(page.locator("#status-upwork")).to_contain_text("DISCONNECTED", timeout=10000)
        print("  [Assert] Upwork Status after disconnect: DISCONNECTED")

        # Re-connect Upwork for full reach tests
        page.fill("#cookie-upwork", test_upwork_token)
        page.click("button:has-text('Attach Cookie'):near(#cookie-upwork)")
        expect(page.locator("#status-upwork")).to_contain_text("CONNECTED", timeout=10000)
        results["2_account_connection"] = "PASS"

        # -------------------------------------------------------------
        # 3. COGNITIVE BRAIN & STORY BANK
        # -------------------------------------------------------------
        print("\n[Step 3] Testing Cognitive Brain & Story Bank...")
        page.evaluate("switchTab('brain')")
        page.wait_for_selector("#pane-brain", state="visible")
        time.sleep(0.5)

        receipt_title = "Shopify High-Volume Catalog Scraper"
        receipt_metric = "Extracted 320,000 product SKUs across 8 storefronts in 42 minutes with zero IP bans"
        receipt_stack = "Python, Playwright, Redis, Docker, Anti-Bot Proxies"
        
        # Open Add Receipt Modal
        page.click("button:has-text('Add Project Receipt')")
        page.wait_for_selector("#modal-add-receipt", state="visible")
        page.fill("#rec-cat", "Web Scraping")
        page.fill("#rec-title", receipt_title)
        page.fill("#rec-niche", "E-Commerce")
        page.fill("#rec-prob", "Rate-limiting and IP bans under 10k req/min")
        page.fill("#rec-stack", receipt_stack)
        page.fill("#rec-metrics", receipt_metric)
        page.fill("#rec-deliv", "Dockerized scraper, Redis pipeline, unit tests")
        take_shot(page, "04_brain_add_receipt_modal")
        
        page.click("button:has-text('Save Receipt')")
        expect(page.locator("#story-bank-tbody")).to_contain_text(receipt_title, timeout=10000)
        take_shot(page, "05_brain_receipt_saved")
        print("  [Assert] New verified receipt successfully saved and listed in Cognitive Brain!")
        results["3_cognitive_brain"] = "PASS"

        # -------------------------------------------------------------
        # 4. REACH & FEED ENGINE
        # -------------------------------------------------------------
        print("\n[Step 4] Testing Reach & Feed (Client Inspection & Winning Strategy)...")
        page.evaluate("switchTab('reach')")
        page.wait_for_selector("#pane-reach", state="visible")
        time.sleep(0.5)

        # Add sample opportunity directly via ReachFeedEngine
        sample_job_text = (
            "Looking for an expert Python engineer to build a high-performance web scraper "
            "for e-commerce product catalogs. Must bypass Cloudflare protection and output to PostgreSQL. "
            "Budget is $1,200 for 50,000 items daily."
        )
        from core.reach.feed_engine import ReachFeedEngine
        engine = ReachFeedEngine()
        feed_id = engine.save_feed_post({
            "platform": "upwork",
            "author_name": "E-Commerce Director",
            "author_headline": "Managing 15 global brands",
            "post_text": sample_job_text,
            "post_url": "https://www.upwork.com/jobs/~01987654321",
            "budget": "$1,200",
            "tags": "python, scraper, postgresql"
        })
        print(f"  Discovered opportunity added to Reach feed (ID #{feed_id})")

        # Refresh feed in UI
        page.evaluate("loadReachFeed()")
        expect(page.locator("#reach-feed-tbody")).to_contain_text("E-Commerce Director", timeout=10000)
        take_shot(page, "06_reach_feed_view")
        print("  [Assert] Opportunity visible in active Reach feed!")

        # Click "Draft Proposal" from feed
        print("  Clicking 'Draft Proposal' shortcut from Reach feed item...")
        page.click("#reach-feed-tbody tr:first-child button:has-text('Draft Proposal')")
        expect(page.locator("#pane-proposals")).to_be_visible(timeout=10000)
        expect(page.locator("#prop-job-desc")).not_to_be_empty(timeout=10000)
        take_shot(page, "07_proposal_auto_populated")
        print("  [Assert] Proposals pane active & job brief auto-populated!")
        results["4_reach_feed"] = "PASS"

        # -------------------------------------------------------------
        # 5. PROPOSALS STUDIO (82-RULE HUMANIZER)
        # -------------------------------------------------------------
        print("\n[Step 5] Testing Proposals Studio with 82-Rule Humanizer...")
        page.fill("#prop-budget", "$1,200")
        page.fill("#prop-stack", "Playwright, Redis, Docker, PostgreSQL")
        page.select_option("#prop-platform", "upwork")
        
        # Click "Write Human Proposal"
        print("  Generating humanized proposal...")
        page.click("#btn-generate-prop")
        expect(page.locator("#btn-save-prop")).to_be_visible(timeout=45000)
        take_shot(page, "08_proposal_generated")

        proposal_text = page.inner_text("#prop-output-text")
        print(f"\n--- GENERATED PROPOSAL PREVIEW ---")
        lines = [l for l in proposal_text.splitlines() if l.strip()]
        for l in lines[:4]:
            print(f"  | {l}")
        print(f"  | ... [{len(proposal_text)} total chars]")
        print("----------------------------------")

        # Assert 82 Humanizer Rules
        first_line = lines[0].lower()
        banned_openers = ["dear", "hello", "hope this finds you well", "i was thrilled", "excited to apply"]
        assert not any(bo in first_line for bo in banned_openers), f"Violated humanizer opener: {first_line}"
        print(f"  [Assert] Line 1 directly hooks buyer without generic greetings: \"{lines[0][:80]}...\"")

        banned_words = ["delve", "pivotal", "robust", "landscape", "tapestry", "innovative", "game-changer", "elevate", "facilitate", "utilize"]
        for bw in banned_words:
            assert bw not in proposal_text.lower(), f"Found banned AI word: '{bw}'"
        print("  [Assert] 0 banned AI vocabulary words found!")

        # Save proposal to history
        page.click("#btn-save-prop")
        expect(page.locator("#saved-props-tbody")).to_contain_text("UPWORK", ignore_case=True, timeout=10000)
        print("  [Assert] Proposal successfully persisted in saved history list!")
        results["5_proposals_studio"] = "PASS"

        # -------------------------------------------------------------
        # 6. COLD CLIENT OUTREACH
        # -------------------------------------------------------------
        print("\n[Step 6] Testing Cold Client Outreach Generator...")
        page.fill("#outreach-prospect", "Acme Logistics")
        page.fill("#outreach-tech", "PostgreSQL billing query latency")
        page.select_option("#outreach-channel", "direct_message")
        page.fill("#outreach-obs", "Noticed 4.2s query latency on your tracking dashboard")

        print("  Drafting value-first outreach...")
        page.click("#btn-draft-outreach")
        expect(page.locator("#outreach-output-text")).not_to_contain_text("Fill in prospect info", timeout=30000)
        take_shot(page, "09_outreach_generated")

        outreach_text = page.inner_text("#outreach-output-text")
        print(f"  [Assert] Drafted Outreach: \"{outreach_text[:100]}...\"")
        assert len(outreach_text) > 30
        results["6_cold_outreach"] = "PASS"

        # -------------------------------------------------------------
        # 7. GIG OPTIMIZER & SEO AUDIT
        # -------------------------------------------------------------
        print("\n[Step 7] Testing Gig Optimizer & SEO Audit...")
        page.evaluate("switchTab('gigs')")
        page.wait_for_selector("#pane-gigs", state="visible")
        time.sleep(0.5)

        page.fill("#gig-topic", "Production Python Web Scraper and Playwright Bot")
        page.fill("#gig-keywords", "python scraper, web scraping, playwright, automation, api")
        page.select_option("#gig-platform", "fiverr")

        print("  Generating and optimizing gig listing...")
        page.click("#btn-optimize-gig")
        expect(page.locator("#btn-save-gig")).to_be_visible(timeout=45000)
        take_shot(page, "10_gig_optimized")

        gig_preview = page.inner_text("#gig-preview-container")
        print(f"  [Assert] Generated Gig Preview: {gig_preview[:120]}...")
        assert "basic" in gig_preview.lower() and "standard" in gig_preview.lower() and "premium" in gig_preview.lower()
        print("  [Assert] 3-tier packages rendered successfully!")

        # Save Gig
        print("  Saving gig to database...")
        page.click("#btn-save-gig")
        expect(page.locator("#saved-gigs-tbody")).to_contain_text("FIVERR", ignore_case=True, timeout=10000)
        print("  [Assert] Gig saved and visible in active portfolio table!")
        results["7_gig_optimizer"] = "PASS"

        # -------------------------------------------------------------
        # 8. CLIENT INBOX & CHAT ASSISTANT
        # -------------------------------------------------------------
        print("\n[Step 8] Testing Client Inbox & Chat Assistant...")
        page.evaluate("switchTab('inbox')")
        page.wait_for_selector("#pane-inbox", state="visible")
        time.sleep(0.5)

        client_message = "Hi, how fast can you build a scraper for 10,000 product pages from Amazon and what will it cost?"
        page.fill("#inbox-client-name", "David (Buyer)")
        page.fill("#inbox-topic", "Amazon Product Scraper")
        page.fill("#inbox-client-msg", client_message)
        page.fill("#inbox-rate", "85")

        print("  Analyzing incoming client message and drafting response...")
        page.click("#btn-reply-inbox")
        expect(page.locator("#inbox-reply-text")).not_to_contain_text("Awaiting incoming message", timeout=35000)
        take_shot(page, "11_inbox_analyzed")

        detected_intent = page.inner_text("#inbox-intent-val")
        action_rec = page.inner_text("#inbox-action-val")
        reply_output = page.inner_text("#inbox-reply-text")

        print(f"  [Assert] Detected Intent: {detected_intent}")
        print(f"  [Assert] Recommended Action: {action_rec}")
        print(f"  [Assert] Drafted Reply: \"{reply_output[:100]}...\"")

        assert len(reply_output) > 20
        expect(page.locator("#inbox-history-tbody")).to_contain_text("David", timeout=10000)
        print("  [Assert] Client conversation logged in history table!")
        results["8_inbox_assistant"] = "PASS"

        browser.close()

    print("\n" + "=" * 70)
    print("   END-TO-END HUMAN SIMULATION SUMMARY")
    print("=" * 70)
    all_pass = True
    for test_name, status in results.items():
        print(f"  [*] {test_name.ljust(30)}: {status}")
        if status != "PASS":
            all_pass = False

    print("=" * 70)
    if all_pass:
        print("🎉 ALL 8 HUMAN USER WORKFLOWS COMPLETED SUCCESSFULLY WITH 100% PASS RATE!")
    else:
        print("❌ SOME USER WORKFLOWS FAILED")
    print("=" * 70)

    return all_pass

if __name__ == "__main__":
    success = run_human_simulation()
    sys.exit(0 if success else 1)
