import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from core.db.database import init_db

from .routes import (
    gigs_router,
    proposals_router,
    seo_router,
    inbox_router,
    competitors_router,
    brain_router,
    profile_router,
    settings_router,
    reach_router
)

app = FastAPI(
    title="FP Nexus Agent API",
    description="Autonomous Freelance Growth Studio for Fiverr, Upwork, and other freelancing platforms.",
    version="1.0.0"
)

# Enable CORS for local dashboards
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize database
init_db()

@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": "fp-nexus-agent", "version": "1.0.0"}

# Register routes
app.include_router(gigs_router, prefix="/api/gigs", tags=["Gigs"])
app.include_router(proposals_router, prefix="/api/proposals", tags=["Proposals"])
app.include_router(seo_router, prefix="/api/seo", tags=["SEO"])
app.include_router(inbox_router, prefix="/api/inbox", tags=["Inbox"])
app.include_router(competitors_router, prefix="/api/competitors", tags=["Competitors"])
app.include_router(brain_router, prefix="/api/brain", tags=["Brain"])
app.include_router(profile_router, prefix="/api/profile", tags=["Profile"])
app.include_router(settings_router, prefix="/api/settings", tags=["Settings"])
app.include_router(reach_router, prefix="/api/reach", tags=["Reach"])

# Mount static frontend
static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
