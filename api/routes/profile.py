import json
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional, Union
from core.db.database import get_connection
from core.skills.profile_optimizer import ProfileOptimizer

router = APIRouter()
prof_opt = ProfileOptimizer()

class OptimizeProfileRequest(BaseModel):
    primary_role: str
    core_skills: Union[List[str], str]
    years_experience: Optional[int] = 5
    platform: Optional[str] = "fiverr"
    specialty_niche: Optional[str] = ""

class SaveProfileRequest(BaseModel):
    platform: str = "fiverr"
    username: Optional[str] = ""
    title_headline: Optional[str] = ""
    bio_description: Optional[str] = ""
    skills: Union[List[str], str] = []
    languages: Optional[str] = "English (Fluent)"
    hourly_rate: Optional[float] = 45.0

@router.get("/")
def get_profile(platform: str = "fiverr"):
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT * FROM profiles WHERE platform = ? ORDER BY id DESC LIMIT 1", (platform,))
        row = c.fetchone()

        if not row:
            return {
                "profile": {
                    "platform": platform,
                    "title_headline": "Senior Full-Stack Engineer & Python Specialist",
                    "bio_description": "I engineer production-grade web systems, fast APIs, and robust scraping engines with clean documentation.",
                    "skills": ["Python", "FastAPI", "React", "Docker", "PostgreSQL", "Playwright"],
                    "hourly_rate": 50.0
                }
            }

        skills_raw = row["skills"] or ""
        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

        return {
            "profile": {
                "id": row["id"],
                "platform": row["platform"],
                "username": row["username"],
                "title_headline": row["title_headline"],
                "bio_description": row["bio_description"],
                "skills": skills,
                "languages": row["languages"],
                "hourly_rate": row["hourly_rate"],
                "last_updated": row["last_updated"]
            }
        }
    finally:
        conn.close()

@router.post("/optimize")
def optimize_profile(req: OptimizeProfileRequest):
    skills_list = req.core_skills if isinstance(req.core_skills, list) else [s.strip() for s in str(req.core_skills).split(",") if s.strip()]
    return prof_opt.optimize_profile(
        primary_role=req.primary_role,
        core_skills=skills_list,
        years_experience=req.years_experience or 5,
        platform_name=req.platform or "fiverr",
        specialty_niche=req.specialty_niche or ""
    )

@router.post("/save")
def save_profile(req: SaveProfileRequest):
    skills_list = req.skills if isinstance(req.skills, list) else [s.strip() for s in str(req.skills).split(",") if s.strip()]
    skills_str = ", ".join(str(s) for s in skills_list)

    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT id FROM profiles WHERE platform = ? LIMIT 1", (req.platform,))
        row = c.fetchone()
        if row:
            c.execute('''
                UPDATE profiles SET
                    username = ?, title_headline = ?, bio_description = ?,
                    skills = ?, languages = ?, hourly_rate = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                req.username or "", req.title_headline or "Software Developer", req.bio_description or "",
                skills_str, req.languages or "English (Fluent)", req.hourly_rate or 45.0, row[0]
            ))
            prof_id = row[0]
        else:
            c.execute('''
                INSERT INTO profiles (platform, username, title_headline, bio_description, skills, languages, hourly_rate, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (
                req.platform, req.username or "", req.title_headline or "Software Developer", req.bio_description or "",
                skills_str, req.languages or "English (Fluent)", req.hourly_rate or 45.0
            ))
            prof_id = c.lastrowid

        conn.commit()
        return {"status": "saved", "profile_id": prof_id}
    finally:
        conn.close()
