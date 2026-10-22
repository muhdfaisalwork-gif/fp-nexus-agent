import os
import json
import time
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
                    if platform == "fiverr":
                        for c in cookies:
                            if c.get("name") in ("_fiverr_session", "user_session", "_fiverr_token", "logged_in") and len(str(c.get("value", ""))) > 5:
                                return True
                    elif platform == "upwork":
                        for c in cookies:
                            if c.get("name") in ("oauth2_global_js_token", "master_access_token", "user_uid", "current_organization_uid") and len(str(c.get("value", ""))) > 5:
                                return True
                    elif len(cookies) > 0:
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

    def _launch_context(self, playwright_instance, platform: str = "fiverr", headless: bool = False, viewport: Optional[Dict[str, int]] = None):
        """
        Launches persistent context with clean lock handling and stealth parameters.
        """
        platform_dir = os.path.join(self.user_data_dir, platform)
        os.makedirs(platform_dir, exist_ok=True)
        self._clean_profile_locks(platform_dir)

        channels = [None, "chrome", "msedge"]
        errors = []

        for ch in channels:
            try:
                kwargs = {
                    "user_data_dir": platform_dir,
                    "headless": headless,
                    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                    "ignore_default_args": ["--enable-automation"],
                    "args": [
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--disable-infobars"
                    ]
                }
                storage_state_file = os.path.join(self.user_data_dir, f"storage_state_{platform}.json")
                if os.path.exists(storage_state_file):
                    kwargs["storage_state"] = storage_state_file
                if ch:
                    kwargs["channel"] = ch
                if viewport:
                    kwargs["viewport"] = viewport
                return playwright_instance.chromium.launch_persistent_context(**kwargs)
            except Exception as e:
                errors.append(f"{ch or 'default'}: {str(e)}")
                continue

        raise RuntimeError(f"Could not launch browser context. Attempted channels: {errors}")

    def save_cookie(self, cookie_string: str, platform: str = "fiverr") -> Dict[str, Any]:
        """
        Directly injects the user's session cookie, saves persistent state, and marks authenticated.
        Supports raw token or full 'name=value' cookie string.
        """
        token = (cookie_string or "").strip().strip('"').strip("'")
        if not token or len(token) < 5:
            return {"status": "error", "message": "Invalid cookie token. Please provide a valid session string."}

        cookie_name = "_fiverr_session" if platform == "fiverr" else "oauth2_global_js_token"
        domain = ".fiverr.com" if platform == "fiverr" else ".upwork.com"

        if "=" in token and not token.startswith("ey"):
            parts = token.split("=", 1)
            cookie_name = parts[0].strip()
            token = parts[1].strip()

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
                f.write(f"authenticated_at={time.time()}\nmethod=cookie\nplatform={platform}\n")
        except Exception as e:
            return {"status": "error", "message": f"Failed to write auth marker: {str(e)}"}

        return {
            "status": "success",
            "message": f"{platform.capitalize()} connected successfully via session cookie!"
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

        return {"status": "success", "message": f"{platform.capitalize()} session disconnected."}

    def open_system_browser(self, platform: str = "fiverr") -> Dict[str, Any]:
        """Opens the user's default system browser (Chrome/Edge/Firefox) directly to the login page."""
        target_url = "https://www.fiverr.com/login" if platform == "fiverr" else "https://www.upwork.com/ab/account-security/login"
        try:
            webbrowser.open(target_url, new=2)
            return {
                "status": "success",
                "message": f"Opened {platform.capitalize()} in your default system browser. Log in, copy your session cookie, and attach it below!"
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
            # If Playwright is missing, open system browser directly
            webbrowser.open(target_url, new=2)
            return {
                "status": "opened_system_browser",
                "message": f"Playwright not found. Opened {platform.capitalize()} in your default browser! Log in, copy your cookie, and attach it below."
            }

        def _action():
            from playwright.sync_api import sync_playwright
            try:
                with sync_playwright() as p:
                    # Clean lock files first
                    platform_dir = os.path.join(self.user_data_dir, platform)
                    self._clean_profile_locks(platform_dir)

                    # Launch standard headed Chromium (isolated to prevent lock errors)
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
                        return {"status": "success", "message": f"{platform.capitalize()} connected successfully! Your session is active."}
                    else:
                        return {"status": "cancelled", "message": "Browser was closed before login was detected. You can also paste your session cookie directly!"}

            except Exception as launch_err:
                # If automated browser cannot be displayed, open in default system browser
                webbrowser.open(target_url, new=2)
                return {
                    "status": "opened_system_browser",
                    "message": f"Automated window could not open ({str(launch_err)}). Opened {platform.capitalize()} in your default browser! Log in and paste your cookie below."
                }

        try:
            return self._run_in_worker_thread(_action, timeout=310)
        except Exception as e:
            webbrowser.open(target_url, new=2)
            return {
                "status": "opened_system_browser",
                "message": f"Opened in system browser: {str(e)}. Please paste session cookie below!"
            }
