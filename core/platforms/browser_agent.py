import os
import json
import time
import re
import urllib.parse
import webbrowser
import concurrent.futures
from typing import Dict, Any, Optional, List

USER_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage", "browser_state")
os.makedirs(USER_DATA_DIR, exist_ok=True)

class FreelanceBrowserAgent:
    """
    Open-source Playwright browser engine for direct, unrestricted freelancing platforms automation:
    - Fiverr & Upwork account connection via session cookies or headed browser login
    - Feed and buyer request scanning
    - Session verification and persistence
    """

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.user_data_dir = USER_DATA_DIR

    def is_playwright_available(self) -> bool:
        try:
            import playwright
            return True
        except ImportError:
            return False

    def is_authenticated(self, platform: str = "fiverr") -> bool:
        """
        Checks if real authenticated session cookie or marker exists for the given platform.
        Checks .authenticated file, storage_state.json, and SQLite database settings.
        """
        auth_file = os.path.join(self.user_data_dir, f".authenticated_{platform}")
        if os.path.exists(auth_file):
            return True

        # Check storage_state.json
        state_file = os.path.join(self.user_data_dir, f"storage_state_{platform}.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cookies = data.get("cookies", [])
                    if len(cookies) > 0 and any(len(str(c.get("value", ""))) > 5 for c in cookies):
                        return True
            except Exception:
                pass

        # Check SQLite database settings table
        try:
            from core.db.database import get_connection
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT value FROM settings WHERE key = ?", (f"{platform.upper()}_CONNECTED",))
            row = c.fetchone()
            conn.close()
            if row and row["value"] == "true":
                return True
        except Exception:
            pass

        return False

    def get_auth_status(self) -> Dict[str, Any]:
        """Returns connection status for supported platforms."""
        return {
            "fiverr_connected": self.is_authenticated("fiverr"),
            "upwork_connected": self.is_authenticated("upwork"),
            "playwright_ready": self.is_playwright_available()
        }

    def _clean_profile_locks(self, platform_dir: str):
        """Removes stale Chromium lock files that cause ProcessSingleton crashes on Windows."""
        if not os.path.exists(platform_dir):
            return
        lock_files = ["lockfile", "SingletonLock", "SingletonSocket", "SingletonCookie"]
        for lf in lock_files:
            p = os.path.join(platform_dir, lf)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    def _run_in_worker_thread(self, fn, *args, timeout: int = 60, **kwargs) -> Any:
        """Runs synchronous Playwright operations in an isolated worker thread."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn, *args, **kwargs)
            try:
                return future.result(timeout=timeout)
            except concurrent.futures.TimeoutError:
                return {"status": "error", "message": f"Browser operation timed out after {timeout} seconds."}

    def parse_cookie_input(self, raw_input: str, platform: str = "fiverr") -> Dict[str, str]:
        """
        Parses any format of cookie string:
        - Raw token (e.g. BAh7... or eyJ...)
        - name=value (e.g. _fiverr_session=xyz)
        - Full Cookie header (e.g. Cookie: _fiverr_session=xyz; logged_in=true; path=/; domain=.fiverr.com)
        - Semicolon-separated cookies
        - JSON array or object from browser extensions (EditThisCookie, Cookie-Editor)
        Returns dict with {"name": cookie_name, "value": clean_token}
        """
        s = (raw_input or "").strip().strip("'\"")
        default_name = "_fiverr_session" if platform == "fiverr" else "oauth2_global_js_token"

        if not s:
            return {"name": default_name, "value": ""}

        # 1. JSON parse attempt (from cookie extensions like EditThisCookie)
        if s.startswith("[") or s.startswith("{"):
            try:
                data = json.loads(s)
                target_names = (
                    "_fiverr_session", "user_session", "_fiverr_token", "logged_in",
                    "oauth2_global_js_token", "master_access_token", "user_uid", "current_organization_uid"
                )
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get("name") in target_names and item.get("value"):
                            return {"name": item["name"], "value": str(item["value"]).strip()}
                    if data and isinstance(data[0], dict) and "value" in data[0]:
                        return {"name": data[0].get("name", default_name), "value": str(data[0]["value"]).strip()}
                elif isinstance(data, dict):
                    for k, v in data.items():
                        if k in target_names:
                            return {"name": k, "value": str(v).strip()}
                    if "cookies" in data and isinstance(data["cookies"], list):
                        for item in data["cookies"]:
                            if isinstance(item, dict) and item.get("name") in target_names and item.get("value"):
                                return {"name": item["name"], "value": str(item["value"]).strip()}
            except Exception:
                pass

        # 2. Strip "Cookie:" or "cookie:" header prefix if present
        if s.lower().startswith("cookie:"):
            s = s[7:].strip()

        # 3. Check if it's explicitly a raw base64 or JWT token (e.g. BAh7..., eyJ...)
        # Base64 Ruby Marshal (_fiverr_session) starts with BAh7. JWT starts with eyJ.
        if s.startswith("BAh7") or s.startswith("eyJ"):
            return {"name": default_name, "value": s}

        # 4. If multiple cookies or attributes separated by semicolons
        if ";" in s:
            parts = [p.strip() for p in s.split(";") if p.strip()]
            target_keys = (
                "_fiverr_session", "user_session", "_fiverr_token", "logged_in",
                "oauth2_global_js_token", "master_access_token", "user_uid", "current_organization_uid"
            )
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k in target_keys and len(v) > 3:
                        return {"name": k, "value": urllib.parse.unquote(v)}
            for part in parts:
                if "=" in part:
                    k, v = part.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip("'\"")
                    if k.lower() not in ("path", "domain", "expires", "samesite", "secure", "httponly", "max-age"):
                        if len(v) > 5:
                            return {"name": k, "value": urllib.parse.unquote(v)}

        # 5. If single string formatted as key=value
        if "=" in s:
            k, v = s.split("=", 1)
            k = k.strip()
            v = v.strip().strip("'\"")
            target_keys = (
                "_fiverr_session", "user_session", "_fiverr_token", "logged_in",
                "oauth2_global_js_token", "master_access_token", "user_uid", "current_organization_uid",
                "token", "session", "auth_token"
            )
            if k in target_keys:
                return {"name": k, "value": urllib.parse.unquote(v)}

            # Base64 padding edge case: e.g. token ending in "==" resulted in k="token", v="="
            if v == "=" or v == "" or (len(v) < 3 and len(k) > 15):
                return {"name": default_name, "value": s}

            if len(k) < 30 and re.match(r'^[a-zA-Z0-9_\-]+$', k) and len(v) >= 3:
                return {"name": k, "value": urllib.parse.unquote(v)}

        # 6. Fallback: Raw token
        return {"name": default_name, "value": urllib.parse.unquote(s)}

    def save_cookie(self, cookie_string: str, platform: str = "fiverr") -> Dict[str, Any]:
        """
        Directly injects the user's session cookie, saves persistent state, and marks authenticated.
        Supports raw token, name=value, full Cookie headers, and extension JSON formats.
        """
        parsed = self.parse_cookie_input(cookie_string, platform=platform)
        cookie_name = parsed["name"]
        token = parsed["value"]

        if not token or len(token) < 5:
            return {"status": "error", "message": "Invalid cookie token. Please provide a valid session string."}

        domain = ".fiverr.com" if platform == "fiverr" else ".upwork.com"
        storage_state_file = os.path.join(self.user_data_dir, f"storage_state_{platform}.json")

        state_data = {
            "cookies": [
                {
                    "name": cookie_name,
                    "value": token,
                    "domain": domain,
                    "path": "/",
                    "expires": int(time.time()) + (180 * 24 * 3600),
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax"
                },
                {
                    "name": cookie_name,
                    "value": token,
                    "domain": f"www{domain}",
                    "path": "/",
                    "expires": int(time.time()) + (180 * 24 * 3600),
                    "httpOnly": True,
                    "secure": True,
                    "sameSite": "Lax"
                }
            ],
            "origins": []
        }

        try:
            with open(storage_state_file, "w", encoding="utf-8") as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            return {"status": "error", "message": f"Failed to save session state: {str(e)}"}

        try:
            with open(os.path.join(self.user_data_dir, f".authenticated_{platform}"), "w", encoding="utf-8") as f:
                f.write(f"authenticated_at={time.time()}\nmethod=cookie\nplatform={platform}\ncookie_name={cookie_name}\n")
        except Exception as e:
            return {"status": "error", "message": f"Failed to write auth marker: {str(e)}"}

        # Also sync to SQLite database settings table so state is doubly persistent!
        try:
            from core.db.database import get_connection
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (f"{platform.upper()}_CONNECTED", "true")
            )
            c.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (f"{platform.upper()}_AUTH_METHOD", "cookie")
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        return {
            "status": "success",
            "message": f"{platform.capitalize()} connected successfully via session cookie ({cookie_name})!"
        }

    def disconnect(self, platform: str = "fiverr") -> Dict[str, Any]:
        """Clears local session state and cookies for the given platform."""
        for filename in [f".authenticated_{platform}", f"storage_state_{platform}.json"]:
            path = os.path.join(self.user_data_dir, filename)
            if os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass

        platform_dir = os.path.join(self.user_data_dir, platform)
        self._clean_profile_locks(platform_dir)

        # Clear in SQLite settings
        try:
            from core.db.database import get_connection
            conn = get_connection()
            c = conn.cursor()
            c.execute(
                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (f"{platform.upper()}_CONNECTED", "false")
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

        return {"status": "success", "message": f"{platform.capitalize()} session disconnected."}

    def open_system_browser(self, platform: str = "fiverr") -> Dict[str, Any]:
        """Opens the user's default system browser (Chrome/Edge/Firefox) directly to the login page."""
        target_url = "https://www.fiverr.com/login" if platform == "fiverr" else "https://www.upwork.com/ab/account-security/login"
        try:
            webbrowser.open(target_url, new=2)
            return {
                "status": "success",
                "message": f"Opened {platform.capitalize()} login page in your browser. Log in, copy your session cookie, and attach it below!"
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed to open system browser: {str(e)}"}

    def launch_interactive_login(self, platform: str = "fiverr") -> Dict[str, Any]:
        """
        Opens a visible browser window so the user can log in to Fiverr or Upwork safely.
        Uses clean browser instance with cookie-sync to avoid lockfile collisions.
        Falls back seamlessly to system default browser if OS blocks automated display.
        """
        target_url = "https://www.fiverr.com/login" if platform == "fiverr" else "https://www.upwork.com/ab/account-security/login"

        if not self.is_playwright_available():
            webbrowser.open(target_url, new=2)
            return {
                "status": "fallback_needed",
                "message": f"Playwright not found. Opened {platform.capitalize()} in your default browser tab! Log in, copy your cookie, and attach it below."
            }

        def _action():
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as p:
                    platform_dir = os.path.join(self.user_data_dir, platform)
                    self._clean_profile_locks(platform_dir)

                    browser = p.chromium.launch(
                        headless=False,
                        args=[
                            "--disable-blink-features=AutomationControlled",
                            "--no-first-run",
                            "--no-default-browser-check"
                        ]
                    )

                    storage_state_file = os.path.join(self.user_data_dir, f"storage_state_{platform}.json")
                    context_kwargs: Dict[str, Any] = {"viewport": {"width": 1280, "height": 850}}
                    if os.path.exists(storage_state_file):
                        context_kwargs["storage_state"] = storage_state_file

                    context = browser.new_context(**context_kwargs)
                    page = context.new_page()

                    try:
                        page.bring_to_front()
                    except Exception:
                        pass

                    try:
                        page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
                    except Exception:
                        pass

                    # Poll up to 300s (5 mins) for user to log in
                    logged_in = False
                    for _ in range(300):
                        try:
                            time.sleep(1)
                            if page.is_closed():
                                break

                            cur_url = page.url.lower()
                            cookies = context.cookies()

                            # Detection via cookies or authenticated URL
                            if platform == "fiverr":
                                has_session = any(c.get("name") in ("_fiverr_session", "user_session", "logged_in", "_fiverr_token") and len(str(c.get("value", ""))) > 5 for c in cookies)
                                on_auth_url = any(k in cur_url for k in ["/manage_gigs", "/seller_dashboard", "/orders", "/inbox", "/users/"]) and "login" not in cur_url
                                if has_session or on_auth_url:
                                    logged_in = True
                                    time.sleep(2)
                                    break
                            elif platform == "upwork":
                                has_session = any(c.get("name") in ("oauth2_global_js_token", "master_access_token", "user_uid") and len(str(c.get("value", ""))) > 5 for c in cookies)
                                on_auth_url = any(k in cur_url for k in ["/nx/find-work", "/ab/find-work", "/freelance-dashboard", "/messages"]) and "login" not in cur_url
                                if has_session or on_auth_url:
                                    logged_in = True
                                    time.sleep(2)
                                    break
                        except Exception:
                            break

                    # Save storage state before closing browser!
                    if logged_in:
                        try:
                            context.storage_state(path=storage_state_file)
                        except Exception:
                            pass

                    try:
                        browser.close()
                    except Exception:
                        pass

                    if logged_in:
                        try:
                            with open(os.path.join(self.user_data_dir, f".authenticated_{platform}"), "w") as f:
                                f.write(f"authenticated_at={time.time()}\nmethod=browser_login\nplatform={platform}\n")
                        except Exception:
                            pass
                        try:
                            from core.db.database import get_connection
                            conn = get_connection()
                            c = conn.cursor()
                            c.execute(
                                "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                                (f"{platform.upper()}_CONNECTED", "true")
                            )
                            conn.commit()
                            conn.close()
                        except Exception:
                            pass
                        return {"status": "success", "message": f"{platform.capitalize()} connected successfully! Your session is active."}
                    else:
                        return {"status": "cancelled", "message": "Browser was closed before login was detected. You can also paste your session cookie directly!"}

            except Exception as launch_err:
                webbrowser.open(target_url, new=2)
                return {
                    "status": "fallback_needed",
                    "message": f"Automated window could not open in this background environment ({str(launch_err)}). Opened {platform.capitalize()} in your browser tab! Please log in and paste your cookie below."
                }

        try:
            return self._run_in_worker_thread(_action, timeout=310)
        except Exception as e:
            webbrowser.open(target_url, new=2)
            return {
                "status": "fallback_needed",
                "message": f"Opened login in browser tab: {str(e)}. Please paste session cookie below!"
            }
