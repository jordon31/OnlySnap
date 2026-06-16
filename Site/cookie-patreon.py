#!python3
#!/usr/bin/env python3
import json
import os
import sys
import time
import shutil
import tkinter as tk

def get_clipboard_content():
    try:
        root = tk.Tk()
        root.withdraw()
        content = root.clipboard_get()
        root.destroy()
        return content
    except:
        return ""

def parse_smart(raw_text):
    data = {}
    lines = raw_text.splitlines()
    target_keys = ["user-agent", "cookie"]

    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue

        if ":" in line:
            parts = line.split(":", 1)
            k = parts[0].strip().lower()
            v = parts[1].strip()
            if k.startswith(":"): k = k[1:]
            if k in target_keys and v:
                data[k] = v

        key_lower = line.lower()
        if key_lower in target_keys:
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if next_line and ":" not in next_line:
                    data[key_lower] = next_line
                    i += 1

        if "session_id=" in line and "cookie" not in data:
            if not line.lower().startswith("cookie:") and not line.lower().startswith("set-cookie:"):
                data["cookie"] = line

        i += 1
    return data

def save_auth(user_agent, cookie_str):
    base_path = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_path, "Configs", "Patreon")
    os.makedirs(config_dir, exist_ok=True)

    auth_file = os.path.join(config_dir, "Auth.json")
    
    # Preserve existing x-csrf-signature
    existing_csrf = ""
    if os.path.exists(auth_file):
        try:
            with open(auth_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
                existing_csrf = existing.get("x-csrf-signature", "")
        except:
            pass
    
    auth_data = {
        "user-agent": user_agent,
        "cookie": cookie_str,
        "x-csrf-signature": existing_csrf
    }

    try:
        with open(auth_file, "w", encoding="utf-8") as f:
            json.dump(auth_data, f, indent=4)
        print(f"\n✅ Auth.json updated: {auth_file}")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def _find_firefox_profile(profiles_dir):
    import glob
    if not os.path.isdir(profiles_dir):
        return None
    for pattern in ["*.default-release", "*.default"]:
        matches = glob.glob(os.path.join(profiles_dir, pattern))
        if matches:
            return matches[0]
    return None

def detect_browser():
    import platform
    system = platform.system()
    home = os.path.expanduser("~")
    browsers = []

    if system == "Windows":
        ff_profile = _find_firefox_profile(os.path.join(home, r"AppData\Roaming\Mozilla\Firefox\Profiles"))
        browsers = [
            ("Brave",
             os.path.expandvars(r"%PROGRAMFILES%\BraveSoftware\Brave-Browser\Application\brave.exe"),
             os.path.join(home, r"AppData\Local\BraveSoftware\Brave-Browser\User Data")),
            ("Brave",
             os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
             os.path.join(home, r"AppData\Local\BraveSoftware\Brave-Browser\User Data")),
            ("Chrome",
             os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
             os.path.join(home, r"AppData\Local\Google\Chrome\User Data")),
            ("Chrome",
             os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
             os.path.join(home, r"AppData\Local\Google\Chrome\User Data")),
            ("Opera",
             os.path.expandvars(r"%LOCALAPPDATA%\Programs\Opera\opera.exe"),
             os.path.join(home, r"AppData\Roaming\Opera Software\Opera Stable")),
            ("Opera",
             os.path.expandvars(r"%PROGRAMFILES%\Opera\opera.exe"),
             os.path.join(home, r"AppData\Roaming\Opera Software\Opera Stable")),
            ("Edge",
             os.path.expandvars(r"%PROGRAMFILES(x86)%\Microsoft\Edge\Application\msedge.exe"),
             os.path.join(home, r"AppData\Local\Microsoft\Edge\User Data")),
            ("Edge",
             os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
             os.path.join(home, r"AppData\Local\Microsoft\Edge\User Data")),
        ]
        if ff_profile:
            browsers.append(("Firefox",
                os.path.expandvars(r"%PROGRAMFILES%\Mozilla Firefox\firefox.exe"),
                ff_profile))
            browsers.append(("Firefox",
                os.path.expandvars(r"%PROGRAMFILES(x86)%\Mozilla Firefox\firefox.exe"),
                ff_profile))
    elif system == "Darwin":  # macOS
        ff_profile = _find_firefox_profile(os.path.join(home, "Library/Application Support/Firefox/Profiles"))
        browsers = [
            ("Brave",
             "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
             os.path.join(home, "Library/Application Support/BraveSoftware/Brave-Browser")),
            ("Chrome",
             "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
             os.path.join(home, "Library/Application Support/Google/Chrome")),
            ("Opera",
             "/Applications/Opera.app/Contents/MacOS/Opera",
             os.path.join(home, "Library/Application Support/com.operasoftware.Opera")),
            ("Edge",
             "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
             os.path.join(home, "Library/Application Support/Microsoft Edge")),
        ]
        if ff_profile:
            browsers.append(("Firefox",
                "/Applications/Firefox.app/Contents/MacOS/firefox",
                ff_profile))
    else:  # Linux
        ff_profile = _find_firefox_profile(os.path.join(home, ".mozilla/firefox"))
        browsers = [
            ("Brave", "/usr/bin/brave-browser",
             os.path.join(home, ".config/BraveSoftware/Brave-Browser")),
            ("Brave", "/usr/bin/brave-browser-stable",
             os.path.join(home, ".config/BraveSoftware/Brave-Browser")),
            ("Chrome", "/usr/bin/google-chrome",
             os.path.join(home, ".config/google-chrome")),
            ("Chrome", "/usr/bin/google-chrome-stable",
             os.path.join(home, ".config/google-chrome")),
            ("Chromium", "/usr/bin/chromium-browser",
             os.path.join(home, ".config/chromium")),
            ("Chromium", "/usr/bin/chromium",
             os.path.join(home, ".config/chromium")),
            ("Opera", "/usr/bin/opera",
             os.path.join(home, ".config/opera")),
            ("Edge", "/usr/bin/microsoft-edge",
             os.path.join(home, ".config/microsoft-edge")),
        ]
        if ff_profile:
            browsers.append(("Firefox", "/usr/bin/firefox", ff_profile))
            browsers.append(("Firefox", "/usr/bin/firefox-esr", ff_profile))
            browsers.append(("Firefox", "/snap/bin/firefox", ff_profile))

    for name, exe_path, data_path in browsers:
        if os.path.isfile(exe_path) and os.path.isdir(data_path):
            return name, exe_path, data_path
    return None, None, None

def is_headless_server():
    import platform
    if platform.system() not in ("Linux", "FreeBSD"):
        return False
    return not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY")

def is_browser_running(browser_name):
    import subprocess, platform
    system = platform.system()
    if system == "Windows":
        proc_map = {"Brave": "brave.exe", "Chrome": "chrome.exe", "Edge": "msedge.exe",
                    "Opera": "opera.exe", "Firefox": "firefox.exe"}
        proc_name = proc_map.get(browser_name, "")
        try:
            result = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {proc_name}"],
                                    capture_output=True, text=True, timeout=5)
            return proc_name.lower() in result.stdout.lower()
        except:
            return False
    else:  # Linux / macOS
        proc_map = {
            "Brave": "brave", "Chrome": "chrome", "Chromium": "chromium",
            "Opera": "opera", "Edge": "msedge", "Firefox": "firefox"
        }
        proc_name = proc_map.get(browser_name, browser_name.lower())
        try:
            result = subprocess.run(["pgrep", "-f", proc_name],
                                    capture_output=True, text=True, timeout=5)
            return result.returncode == 0
        except:
            return False

def auto_scrape():
    if is_headless_server():
        print("❌ No display server detected (headless server).")
        print("   Use clipboard mode or add cookies manually to Auth.json.")
        return None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Installing Playwright (pip only, using your browser)...")
        os.system(f'"{sys.executable}" -m pip install playwright')
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("❌ Playwright install failed.")
            return None

    browser_name, browser_path, user_data = detect_browser()
    if not browser_path:
        print("⚠️  No supported browser found. Downloading Playwright Chromium...")
        os.system(f'"{sys.executable}" -m playwright install chromium')
        browser_name = "Chromium (Playwright)"
        browser_path = None
        user_data = None

    is_firefox = browser_name == "Firefox"
    use_playwright_browser = browser_path is None

    if not use_playwright_browser and is_browser_running(browser_name):
        print(f"\n⚠️  {browser_name} is open. Close it first to use your profile.")
        input("   Press ENTER after closing the browser...")
        if is_browser_running(browser_name):
            print(f"❌ {browser_name} is still running. Aborting.")
            return None

    print(f"\n🌐 Opening {browser_name}...")
    print("   Reading cookies after page load...\n")

    captured = {}

    with sync_playwright() as p:
        try:
            if use_playwright_browser:
                import tempfile
                tmp_dir = tempfile.mkdtemp()
                context = p.chromium.launch_persistent_context(
                    tmp_dir,
                    headless=False,
                    viewport={"width": 1280, "height": 800},
                    args=["--disable-blink-features=AutomationControlled"],
                    ignore_default_args=["--enable-automation"]
                )
            elif is_firefox:
                context = p.firefox.launch_persistent_context(
                    user_data,
                    executable_path=browser_path,
                    headless=False, #captcha
                    viewport={"width": 1280, "height": 800},
                )
            else:
                context = p.chromium.launch_persistent_context(
                    user_data,
                    executable_path=browser_path,
                    headless=False,
                    viewport={"width": 1280, "height": 800},
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-first-run",
                        "--no-default-browser-check",
                        "--profile-directory=Default",
                        "--disable-session-crashed-bubble",
                        "--no-restore-state"
                    ],
                    ignore_default_args=["--enable-automation"]
                )
        except Exception as e:
            print(f"❌ Browser launch failed: {e}")
            print("   Make sure the browser is fully closed and try again.")
            return None

        page = context.new_page()
        for old_page in context.pages:
            if old_page != page:
                try: old_page.close()
                except: pass

        print("   Navigating to patreon.com/messages...")
        try:
            page.goto("https://www.patreon.com/messages?mode=user&tab=chats", wait_until="domcontentloaded", timeout=15000)
            print(f"   Page loaded. URL: {page.url}")
        except:
            print(f"   Page load slow but continuing... URL: {page.url}")

        time.sleep(1)

        try:
            browser_cookies = context.cookies("https://www.patreon.com")
            cookie_dict = {c['name']: c['value'] for c in browser_cookies}
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in browser_cookies])

            print(f"   Cookies found: {list(cookie_dict.keys())}")

            if cookie_dict.get("session_id"):
                user_agent = page.evaluate("() => navigator.userAgent")
                captured = {
                    "user-agent": user_agent,
                    "cookie": cookie_str,
                    "x-csrf-signature": "",
                }
                print(f"   ✅ session_id: {cookie_dict['session_id'][:15]}...")
            else:
                print("   ❌ No session_id cookie — not logged in!")

        except Exception as e:
            print(f"   ❌ Cookie read error: {e}")

        try:
            context.close()
        except: pass

    if not captured:
        print("\n❌ Failed to capture cookies.")
        return None

    return captured

def clipboard_scrape():
    print("Checking clipboard...")
    raw_text = get_clipboard_content()
    extracted = parse_smart(raw_text)

    has_headers = False
    if extracted.get("user-agent") and extracted.get("cookie"):
        if "session_id=" in extracted.get("cookie"):
            has_headers = True

    if not has_headers:
        print("\nERROR: Invalid or incomplete data!")
        print("Copy the entire 'Headers' section of a Patreon request from DevTools.")
        print("Make sure it contains both 'user-agent' and 'cookie' with 'session_id'.")
        time.sleep(4)
        return None

    print("Data looks valid. Processing...")
    return extracted

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("Patreon Cookie Manager")
    print("---------------------------------------")
    print(" [1] Auto (opens browser)")
    print(" [2] Clipboard (manual copy from DevTools)")
    print("---------------------------------------")

    choice = input("Select mode (1/2): ").strip()

    if choice == "1":
        result = auto_scrape()
        if result:
            save_auth(result["user-agent"], result["cookie"])
        else:
            print("\nFallback: try clipboard mode? (y/n)")
            if input().strip().lower() == 'y':
                result = clipboard_scrape()
                if result:
                    save_auth(result.get("user-agent", ""), result.get("cookie", ""))
    elif choice == "2":
        result = clipboard_scrape()
        if result:
            save_auth(result.get("user-agent", ""), result.get("cookie", ""))
    else:
        print("Invalid choice.")

    print("\nDone.")
    time.sleep(1.5)

if __name__ == "__main__":
    if "--auto" in sys.argv:
        result = auto_scrape()
        if result:
            save_auth(result["user-agent"], result["cookie"])
        else:
            sys.exit(1)
    else:
        main()