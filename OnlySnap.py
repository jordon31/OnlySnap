#!python3
#!/usr/bin/env python3
import os
import sys
import re
import subprocess
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Label, Button
from textual import on

CURRENT_VERSION = "1.0.6"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/jordon31/OnlySnap/main/OnlySnap.py"

def check_for_updates():
    try:
        import requests
        response = requests.get(GITHUB_RAW_URL, timeout=5)
        if response.status_code == 200:
            match = re.search(r'CURRENT_VERSION\s*=\s*[\'"]([^\'"]+)[\'"]', response.text)
            if match:
                remote_version = match.group(1)
                if remote_version != CURRENT_VERSION:
                    return True, remote_version
        return False, None
    except:
        return False, None

class OnlySnapLauncher(App):
    CSS = """
    Screen {
        layout: vertical;
        align: center middle;
        background: #191724;
        color: #e0def4;
    }

    #container {
        width: 60%;
        height: auto;
        padding: 2 4;
        border: heavy #ebbcba;
        background: #1f1d2e;
        align: center middle;
    }

    .title {
        text-style: bold;
        color: #f6c177;
        margin-bottom: 2;
        content-align: center middle;
        width: 100%;
    }
    
    .desc {
        color: #9ccfd8;
        margin-bottom: 2;
        content-align: center middle;
        width: 100%;
    }

    Button {
        width: 100%;
        margin: 1 0;
        text-style: bold;
    }

    #btn-onlyfans {
        background: #008ccf;
        color: white;
    }

    #btn-patreon {
        background: #f96854;
        color: white;
    }
    
    #btn-exit {
        background: #eb6f92;
        color: white;
        margin-top: 2;
    }
    .update-label {
        color: #eb6f92;
        content-align: center middle;
        width: 100%;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="container"):
            yield Label(f"ONLYSNAP TUI HUB  v{CURRENT_VERSION}", classes="title")
            yield Label("", id="update-label", classes="update-label")
            yield Label("Select which scraper you want to run", classes="desc")
            yield Button("ONLYFANS", id="btn-onlyfans")
            yield Button("PATREON", id="btn-patreon")
            yield Button("EXIT", id="btn-exit")

    def on_mount(self) -> None:
        self.run_worker(self._check_updates_async)

    async def _check_updates_async(self) -> None:
        import asyncio
        has_update, remote_ver = await asyncio.to_thread(check_for_updates)
        if has_update:
            lbl = self.query_one("#update-label")
            lbl.update(f"⚡ Update available: v{remote_ver}  →  github.com/jordon31/OnlySnap")

    @on(Button.Pressed)
    def handle_button(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        base_dir = os.path.dirname(os.path.abspath(__file__))
        site_dir = os.path.join(base_dir, "Site")

        if button_id == "btn-exit":
            self.exit()
            return
            
        script_name = ""
        if button_id == "btn-onlyfans":
            script_name = "OnlyFans.py"
            
            # Check if cookies exist
            auth_path = os.path.join(site_dir, "Configs", "OnlyFans", "Auth.json")
            needs_cookies = True
            if os.path.exists(auth_path):
                try:
                    import json
                    with open(auth_path, "r", encoding="utf-8") as f:
                        auth = json.load(f)
                    if auth.get("sess", "").strip():
                        needs_cookies = False
                except: pass
            
            if needs_cookies:
                with self.suspend():
                    cookie_script = os.path.join(site_dir, "cookie-onlyfans.py")
                    # Headless server: manual mode
                    is_headless = (os.name != 'nt' and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'))
                    if is_headless:
                        print("\n⚠️  No cookies found (headless server). Launching manual cookie setup...")
                        subprocess.run([sys.executable, cookie_script], cwd=site_dir)
                    else:
                        print("\n⚠️  No cookies found. Starting auto cookie scrape...")
                        subprocess.run([sys.executable, cookie_script, "--auto"], cwd=site_dir)
                    try:
                        import json as _json
                        with open(auth_path, "r", encoding="utf-8") as f:
                            check = _json.load(f)
                        if not check.get("sess", "").strip():
                            print("\n❌ Cookie scrape failed.")
                            input("Press Enter to return to Hub...")
                            return
                        print("\n✅ Cookies ready! Launching OnlyFans...\n")
                        import time; time.sleep(1)
                    except Exception as e:
                        print(f"\n❌ Auto scrape error: {e}")
                        input("Press Enter to return to Hub...")
                        return

        elif button_id == "btn-patreon":
            script_name = "Patreon.py"
            
            # Check if cookies exist
            auth_path = os.path.join(site_dir, "Configs", "Patreon", "Auth.json")
            needs_cookies = True
            if os.path.exists(auth_path):
                try:
                    import json
                    with open(auth_path, "r", encoding="utf-8") as f:
                        auth = json.load(f)
                    if "session_id=" in auth.get("cookie", ""):
                        needs_cookies = False
                except: pass
            
            if needs_cookies:
                with self.suspend():
                    cookie_script = os.path.join(site_dir, "cookie-patreon.py")
                    is_headless = (os.name != 'nt' and not os.environ.get('DISPLAY') and not os.environ.get('WAYLAND_DISPLAY'))
                    if is_headless:
                        print("\n⚠️  No Patreon cookies found (headless server). Launching manual cookie setup...")
                        subprocess.run([sys.executable, cookie_script], cwd=site_dir)
                    else:
                        print("\n⚠️  No Patreon cookies found. Starting auto cookie scrape...")
                        subprocess.run([sys.executable, cookie_script, "--auto"], cwd=site_dir)
                    try:
                        import json as _json
                        with open(auth_path, "r", encoding="utf-8") as f:
                            check = _json.load(f)
                        if "session_id=" not in check.get("cookie", ""):
                            print("\n❌ Cookie scrape failed.")
                            input("Press Enter to return to Hub...")
                            return
                        print("\n✅ Cookies ready! Launching Patreon...\n")
                        import time; time.sleep(1)
                    except Exception as e:
                        print(f"\n❌ Auto scrape error: {e}")
                        input("Press Enter to return to Hub...")
                        return
        script_path = os.path.join(site_dir, script_name)

        if os.path.exists(script_path):
            with self.suspend():
                try:
                    result = subprocess.run([sys.executable, script_path], cwd=site_dir)
                    if result.returncode != 0:
                        input(f"\n[!] {script_name} exited with error (Code {result.returncode}).\nMissing Auth.json or Config.json? Press Enter to return to Hub...")
                except Exception as e:
                    input(f"\n[!] Error launching {script_name}:\n{e}\nPress Enter...")
        else:
            with self.suspend():
                input(f"\n[!] Error: {script_name} not found.\nPress Enter...")


if __name__ == "__main__":
    # OS specifics for terminal title
    import platform
    import ctypes
    system = platform.system()
    if system == "Windows":
        try: ctypes.windll.kernel32.SetConsoleTitleW("OnlySnap Hub")
        except: pass
    else:
        sys.stdout.write(f"\033]0;OnlySnap Hub\a")
        sys.stdout.flush()

    app = OnlySnapLauncher()
    app.run()
