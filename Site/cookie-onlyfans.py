#!/usr/bin/env python3
#!python3
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
    
    target_keys = [
        "user-agent", "x-hash", "x-bc", "user-id", "cookie", 
        "x-of-rev", "sign", "accept"
    ]

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
            
            if k in target_keys or k == "cookie":
                if v: 
                    data[k] = v

        key_lower = line.lower()
        if key_lower in target_keys:
            if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if next_line: 
                    data[key_lower] = next_line
                    i += 1
        
        if "sess=" in line and "cookie" not in data:
            if not line.lower().startswith("cookie:") and not line.lower().startswith("set-cookie:"):
                data["cookie"] = line

        i += 1

    return data

def parse_cookies(cookie_str):
    cookies = {}
    if not cookie_str: return cookies
    parts = cookie_str.split(';')
    for part in parts:
        if '=' in part:
            k, v = part.strip().split('=', 1)
            cookies[k.strip()] = v.strip()
    return cookies

def save_auth(extracted, cookies):
    base_path = os.path.dirname(os.path.abspath(__file__))
    config_dir = os.path.join(base_path, "Configs", "OnlyFans")
    
    if not os.path.exists(config_dir): 
        os.makedirs(config_dir)

    config_file = os.path.join(config_dir, "Config.json")
    config_example = os.path.join(config_dir, "Config.json.example")

    if not os.path.exists(config_file) and os.path.exists(config_example):
        try:
            shutil.copy(config_example, config_file)
        except: pass

    auth_file = os.path.join(config_dir, "Auth.json")
    auth_example = os.path.join(config_dir, "Auth.json.example")
    
    current_auth = {}

    if os.path.exists(auth_file):
        try:
            with open(auth_file, "r", encoding="utf-8") as f:
                current_auth = json.load(f)
        except:
            current_auth = {}
    
    elif os.path.exists(auth_example):
        print("Creating new Auth.json from example...")
        try:
            shutil.copy(auth_example, auth_file)
            with open(auth_file, "r", encoding="utf-8") as f:
                current_auth = json.load(f)
        except: pass

    auth_update = {
        "user-agent": extracted.get("user-agent", current_auth.get("user-agent", "")),
        "user-id": extracted.get("user-id", cookies.get("auth_id", current_auth.get("user-id", ""))),
        "x-bc": extracted.get("x-bc", cookies.get("fp", current_auth.get("x-bc", ""))),
        "x-hash": extracted.get("x-hash", current_auth.get("x-hash", "")),
        "x-of-rev": extracted.get("x-of-rev", current_auth.get("x-of-rev", "")),
        "sess": cookies.get("sess", current_auth.get("sess", "")),
        "st": cookies.get("st", current_auth.get("st", "")),
        "cf_bm": cookies.get("__cf_bm", current_auth.get("cf_bm", "")),
        "cfuvid": cookies.get("_cfuvid", current_auth.get("cfuvid", "")),
        "fp": cookies.get("fp", current_auth.get("fp", "")),
    }

    current_auth.update(auth_update)

    try:
        with open(auth_file, "w", encoding="utf-8") as f:
            json.dump(current_auth, f, indent=4)
        print(f"\n✅ Auth.json updated: {auth_file}")
        return True
    except Exception as e:
        print(f"Error saving file: {e}")
        return False

def _find_firefox_profile(profiles_dir):
    import glob
    if not os.path.isdir(profiles_dir):
        return None
    # Look for *.default-release first, then *.default
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
        # Firefox at the end (Chromium preferred)
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
    # Headless server: no GUI available
    if is_headless_server():
        print("❌ No display server detected (headless server).")
        print("   Use clipboard mode or add cookies manually to Auth.json.")
        return None

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Installing Playwright...")
        os.system(f'"{sys.executable}" -m pip install playwright')
        os.system(f'"{sys.executable}" -m playwright install chromium firefox')
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            print("❌ Playwright install failed. Use clipboard mode.")
            return None

    browser_name, browser_path, user_data = detect_browser()
    if not browser_path:
        print("❌ No supported browser found.")
        return None

    is_firefox = browser_name == "Firefox"

    if is_browser_running(browser_name):
        print(f"\n⚠️  {browser_name} is open. Close it first to use your profile.")
        input("   Press ENTER after closing the browser...")
        if is_browser_running(browser_name):
            print(f"❌ {browser_name} is still running. Aborting.")
            return None

    captured = {}

    print(f"\n🌐 Opening {browser_name} (your profile)...")
    print("   Reading cookies after page load...\n")

    with sync_playwright() as p:
        try:
            if is_firefox:
                context = p.firefox.launch_persistent_context(
                    user_data,
                    executable_path=browser_path,
                    headless=False,
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

        # Close restored tabs, open fresh one
        page = context.new_page()
        for old_page in context.pages:
            if old_page != page:
                try: old_page.close()
                except: pass

        print("   Navigating to onlyfans.com...")
        try:
            page.goto("https://onlyfans.com/my/chats/", wait_until="domcontentloaded", timeout=15000)
            print(f"   Page loaded. URL: {page.url}")
        except:
            print(f"   Page load slow but continuing... URL: {page.url}")
        
        time.sleep(1)

        # Read all cookies from browser
        try:
            browser_cookies = context.cookies("https://onlyfans.com")
            cookie_dict = {c['name']: c['value'] for c in browser_cookies}
            cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in browser_cookies])
            
            print(f"   Cookies found: {list(cookie_dict.keys())}")
            
            if cookie_dict.get("sess"):
                # Try to get x-of-rev from page
                x_of_rev = ""
                try:
                    x_of_rev = page.evaluate("() => { try { return window.__NEXT_DATA__?.buildId || '' } catch(e) { return '' } }")
                except: pass
                if not x_of_rev:
                    try:
                        # Try from script tags
                        scripts = page.query_selector_all("script[src*='static']")
                        for s in scripts:
                            src = s.get_attribute("src") or ""
                            if "/prod/f/" in src:
                                parts = src.split("/prod/f/")
                                if len(parts) > 1:
                                    x_of_rev = parts[1].split("/")[0]
                                    break
                    except: pass
                
                captured = {
                    "user-agent": page.evaluate("() => navigator.userAgent"),
                    "user-id": cookie_dict.get("auth_id", ""),
                    "x-bc": cookie_dict.get("fp", ""),
                    "x-hash": "",
                    "x-of-rev": x_of_rev,
                    "cookie": cookie_str,
                }
                print(f"   ✅ user-id: {captured['user-id']}")
                print(f"   ✅ sess: {cookie_dict['sess'][:10]}...")
                print(f"   ✅ x-of-rev: {x_of_rev}")
            else:
                print("   ❌ No sess cookie — not logged in!")
                
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
    if extracted.get("user-agent") or extracted.get("cookie") or "sess=" in raw_text:
        has_headers = True

    if not has_headers:
        print("\nERROR: No Headers found!")
        print("Copy the 'onlyfans.com/api2/v2/lists?filter=chat' section from DevTools.")
        time.sleep(3)
        return None

    cookies = parse_cookies(extracted.get("cookie", ""))
    
    if not extracted.get("user-agent") and not cookies.get("sess"):
        print("\nData looks incomplete (Missing UA or Session). Aborting.")
        time.sleep(2)
        return None

    print("Data looks valid. Processing...")
    return extracted

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("OnlyFans Cookie Manager")
    print("---------------------------------------")
    print(" [1] Auto (opens browser)")
    print(" [2] Clipboard (manual copy from DevTools)")
    print("---------------------------------------")
    
    choice = input("Select mode (1/2): ").strip()
    
    if choice == "1":
        result = auto_scrape()
        if result:
            cookies = parse_cookies(result.get("cookie", ""))
            save_auth(result, cookies)
        else:
            print("\nFallback: try clipboard mode? (y/n)")
            if input().strip().lower() == 'y':
                result = clipboard_scrape()
                if result:
                    cookies = parse_cookies(result.get("cookie", ""))
                    save_auth(result, cookies)
    elif choice == "2":
        result = clipboard_scrape()
        if result:
            cookies = parse_cookies(result.get("cookie", ""))
            save_auth(result, cookies)
    else:
        print("Invalid choice.")
    
    print("\nDone.")
    time.sleep(1.5)

if __name__ == "__main__":
    if "--auto" in sys.argv:
        result = auto_scrape()
        if result:
            cookies = parse_cookies(result.get("cookie", ""))
            save_auth(result, cookies)
        else:
            sys.exit(1)
    else:
        main()