import os
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional

class ReachReader:
    """
    Dual-backend internet reader:
    - Backend 1 (High-speed Jina Reader): Converts web pages and public gigs into clean Markdown.
    - Backend 2 (Direct HTTP / Browser DOM fallback): For static HTML or fallback extraction.
    """

    def __init__(self):
        self.jina_prefix = "https://r.jina.ai/"

    def read_url(self, url: str, timeout: int = 12) -> Dict[str, Any]:
        url = (url or "").strip()
        if not url or url.lower() in ("http://", "https://"):
            return {
                "status": "error",
                "url": url,
                "message": "A valid URL is required."
            }
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"https://{url}"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/markdown, text/html, application/xhtml+xml, text/plain;q=0.9, */*;q=0.8"
        }

        # 1. Try Jina Reader via requests (handles SSL and redirects cleanly)
        import requests
        import re
        try:
            jina_url = f"{self.jina_prefix}{url}"
            resp = requests.get(jina_url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                content = resp.text
                if content and len(content.strip()) > 80 and "Captcha" not in content and "Access Denied" not in content:
                    lines = [line.strip() for line in content.split("\n") if line.strip()]
                    title_match = re.search(r'<title>(.*?)</title>', content, re.IGNORECASE)
                    if title_match:
                        title = title_match.group(1).strip()
                    elif lines and lines[0].startswith("#"):
                        title = lines[0].lstrip("#").strip()
                    elif lines:
                        title = lines[0].replace("#", "").strip()
                    else:
                        title = "Extracted Gig / Profile"

                    return {
                        "status": "success",
                        "backend": "jina_reader",
                        "url": url,
                        "title": title[:120],
                        "content": content[:6000],
                        "summary": content[:400] + "..." if len(content) > 400 else content
                    }
        except Exception:
            pass

        # 2. Try direct HTTP request fallback via requests
        try:
            resp = requests.get(url, headers=headers, timeout=timeout)
            if resp.status_code == 200:
                html = resp.text
                title_match = re.search(r'<title>(.*?)</title>', html, re.IGNORECASE)
                page_title = title_match.group(1).strip() if title_match else "Extracted Web Page"
                clean = re.sub(r'<script[\s\S]*?</script>', '', html, flags=re.IGNORECASE)
                clean = re.sub(r'<style[\s\S]*?</style>', '', clean, flags=re.IGNORECASE)
                clean = re.sub(r'<[^>]+>', ' ', clean)
                clean = re.sub(r'\s+', ' ', clean).strip()
                if len(clean) > 80:
                    return {
                        "status": "success",
                        "backend": "direct_http",
                        "url": url,
                        "title": page_title[:120],
                        "content": clean[:5000],
                        "summary": clean[:400] + "..."
                    }

        except Exception as e:
            return {
                "status": "error",
                "url": url,
                "message": f"Failed to extract URL: {e}"
            }

        return {
            "status": "error",
            "url": url,
            "message": "Unable to extract content from the URL."
        }
