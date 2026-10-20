import os
import sqlite3
import json
from typing import Any, Dict, List, Optional
from datetime import datetime

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")
DB_PATH = os.path.join(DB_DIR, "fp_nexus.db")

os.makedirs(DB_DIR, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def _init_tables(conn):
    conn.execute("PRAGMA journal_mode = WAL;")
    cursor = conn.cursor()

    # 1. Gigs Table (Fiverr Gigs, Upwork Project Catalog)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gigs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT DEFAULT 'fiverr',
            title TEXT NOT NULL,
            category TEXT,
            subcategory TEXT,
            search_tags TEXT,
            description TEXT NOT NULL,
            basic_tier_name TEXT,
            basic_tier_desc TEXT,
            basic_tier_price REAL DEFAULT 50.0,
            basic_tier_delivery_days INTEGER DEFAULT 2,
            standard_tier_name TEXT,
            standard_tier_desc TEXT,
            standard_tier_price REAL DEFAULT 150.0,
            standard_tier_delivery_days INTEGER DEFAULT 4,
            premium_tier_name TEXT,
            premium_tier_desc TEXT,
            premium_tier_price REAL DEFAULT 350.0,
            premium_tier_delivery_days INTEGER DEFAULT 7,
            faqs TEXT,
            requirements TEXT,
            status TEXT DEFAULT 'active',
            seo_score REAL DEFAULT 0.0,
            flesch_score REAL DEFAULT 0.0,
            last_optimized_at TEXT DEFAULT CURRENT_TIMESTAMP,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Profiles Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT DEFAULT 'fiverr',
            username TEXT,
            title_headline TEXT,
            bio_description TEXT,
            skills TEXT,
            languages TEXT,
            hourly_rate REAL DEFAULT 45.0,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 3. Story Bank (Verified Case Studies & Receipts)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS story_bank (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            client_niche TEXT,
            problem TEXT NOT NULL,
            solution_stack TEXT NOT NULL,
            verified_metrics TEXT NOT NULL,
            duration_days INTEGER DEFAULT 7,
            deliverables TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 4. Proposals Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS proposals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT DEFAULT 'upwork',
            job_title TEXT,
            job_description TEXT NOT NULL,
            client_budget TEXT,
            proposal_text TEXT NOT NULL,
            humanizer_score REAL DEFAULT 100.0,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 5. SEO Audits Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS seo_audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gig_id INTEGER,
            audit_type TEXT DEFAULT 'weekly_keyword_check',
            previous_tags TEXT,
            recommended_tags TEXT,
            score REAL DEFAULT 0.0,
            keyword_density_data TEXT,
            recommendations TEXT,
            status TEXT DEFAULT 'pending_review',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (gig_id) REFERENCES gigs (id) ON DELETE CASCADE
        )
    ''')

    # 6. Competitor Scans Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS competitor_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT DEFAULT 'fiverr',
            url TEXT NOT NULL,
            competitor_name TEXT,
            gig_title TEXT,
            price_range TEXT,
            extracted_tags TEXT,
            review_count INTEGER DEFAULT 0,
            rating REAL DEFAULT 5.0,
            key_takeaways TEXT,
            counter_strategy TEXT,
            scanned_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 7. Inbox Conversations Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inbox_conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            platform TEXT DEFAULT 'fiverr',
            client_name TEXT,
            project_topic TEXT,
            last_client_message TEXT NOT NULL,
            detected_intent TEXT,
            drafted_reply TEXT NOT NULL,
            status TEXT DEFAULT 'draft',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 8. Settings Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Seed default settings if empty
    default_settings = [
        ("LLM_PROVIDER", "openrouter"),
        ("OPENROUTER_MODEL", "qwen/qwen3.8-27b:free"),
        ("OPENROUTER_API_KEY", os.getenv("OPENROUTER_API_KEY", "")),
        ("OLLAMA_MODEL", "deepcoder:1.5b"),
        ("DEFAULT_PLATFORM", "fiverr"),
        ("SEO_WEEKLY_INTERVAL_DAYS", "7"),
        ("SEO_DEEP_AUDIT_INTERVAL_DAYS", "14")
    ]
    for k, v in default_settings:
        cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Create performance indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_gigs_platform_status ON gigs(platform, status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_proposals_platform ON proposals(platform);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_seo_audits_gig ON seo_audits(gig_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_story_bank_cat ON story_bank(category);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_inbox_platform ON inbox_conversations(platform);")

    # Seed initial Story Bank receipts if empty
    cursor.execute("SELECT COUNT(*) FROM story_bank")
    if cursor.fetchone()[0] == 0:
        seed_story_bank(cursor)

    conn.commit()


def init_db():
    conn = get_connection()
    try:
        _init_tables(conn)
    finally:
        conn.close()


def seed_story_bank(cursor):
    """Seed real, concrete builder receipts so the agent never hallucinates claims."""
    initial_receipts = [
        (
            "Backend & API",
            "High-Concurrency Order Processing Microservice",
            "Fintech / Trading",
            "Client was experiencing checkout timeouts and 2.4s order execution latency during market open spikes.",
            "FastAPI, Redis pub/sub queue, PostgreSQL connection pool, async worker threads, Docker",
            "Cut median execution latency from 2,400ms to 380ms. Eliminated timeout errors across 45,000 requests/minute.",
            14,
            "Production-ready FastAPI service, Docker compose, benchmark test suite (Locust), Redis setup documentation"
        ),
        (
            "Full Stack Web App",
            "B2B SaaS Analytics & Team Workspace Dashboard",
            "SaaS / Productivity",
            "Manual CSV parsing and spreadsheets taking 12+ hours/week with zero real-time visibility.",
            "Next.js, TypeScript, TailwindCSS, Node.js backend, Stripe subscription billing, Prisma ORM",
            "Saved client 14 manual operational hours weekly. Integrated 3-tier subscription billing with webhook reconciliation.",
            21,
            "Complete SaaS web app, responsive UI, Stripe portal, automated weekly email digest reports"
        ),
        (
            "Web Scraping & Automation",
            "Multi-Marketplace Price Monitor & Alert Bot",
            "E-Commerce",
            "Client was losing sales due to delayed competitor price adjustments across 8 e-commerce stores.",
            "Python, Playwright headless browser, BeautifulSoup4, SQLite, Telegram & Discord webhook bots",
            "Automated scraping of 12,000 product SKUs daily in 18 minutes with anti-bot fingerprint rotation. Zero IP blocks in 9 months.",
            7,
            "Python scraping scripts, scheduled cron job, alert webhook integration, clean CSV/JSON exports"
        ),
        (
            "AI & Workflow Integration",
            "Autonomous Customer Support & Ticket Triage Agent",
            "E-Commerce & Logistics",
            "Support staff overwhelmed by 600+ repetitive shipping and return status tickets per day.",
            "Python, FastAPI, OpenAI/OpenRouter LLM embeddings, Zendesk & Shopify REST APIs",
            "Autonomously resolved 68% of first-touch tickets with zero human intervention. Reduced average resolution time from 4 hours to 90 seconds.",
            10,
            "FastAPI middleware bot, Zendesk webhook triggers, evaluation test suite, admin dashboard"
        )
    ]
    cursor.executemany('''
        INSERT INTO story_bank (
            category, title, client_niche, problem, solution_stack,
            verified_metrics, duration_days, deliverables
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', initial_receipts)
