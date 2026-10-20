from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any, Optional
import os
from core.db.database import get_connection
from core.llm.providers import OpenRouterProvider

router = APIRouter()

class UpdateSettingsRequest(BaseModel):
    LLM_PROVIDER: Optional[str] = None
    OPENROUTER_MODEL: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    OLLAMA_MODEL: Optional[str] = None
    OLLAMA_BASE_URL: Optional[str] = None
    DEFAULT_PLATFORM: Optional[str] = None
    SEO_WEEKLY_INTERVAL_DAYS: Optional[str] = None
    SEO_DEEP_AUDIT_INTERVAL_DAYS: Optional[str] = None

@router.get("/")
def get_settings():
    conn = get_connection()
    try:
        c = conn.cursor()
        c.execute("SELECT key, value FROM settings")
        rows = c.fetchall()

        settings_dict = {}
        for r in rows:
            settings_dict[r["key"]] = r["value"]

        # Mask API keys for UI safety if present
        masked_display = ""
        for k in list(settings_dict.keys()):
            if k.endswith("_API_KEY"):
                raw_val = settings_dict.get(k) or ""
                if raw_val and len(raw_val) > 12:
                    masked = raw_val[:8] + "..." + raw_val[-4:]
                elif raw_val:
                    masked = "***"
                else:
                    masked = ""
                settings_dict[k] = masked
                if k == "OPENROUTER_API_KEY":
                    masked_display = masked

        return {
            "settings": settings_dict,
            "masked_api_key": masked_display,
            "supported_providers": ["openrouter", "ollama", "openai", "anthropic", "gemini"],
            "free_models": list(OpenRouterProvider.FREE_MODELS)
        }
    finally:
        conn.close()

@router.post("/")
def update_settings(req: UpdateSettingsRequest):
    conn = get_connection()
    try:
        c = conn.cursor()
        req_dict = req.model_dump(exclude_unset=True) if hasattr(req, "model_dump") else req.dict(exclude_unset=True)
        updated_keys = []
        for k, v in req_dict.items():
            if v is not None:
                if k.endswith("_API_KEY") and ("..." in str(v) or str(v).strip() in ("", "***")):
                    continue
                c.execute("INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)", (k, str(v)))
                updated_keys.append(k)

        conn.commit()
        return {"status": "updated", "updated_keys": updated_keys}
    finally:
        conn.close()
