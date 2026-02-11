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

def main():
    os.system('cls' if os.name == 'nt' else 'clear')
    print("OnlyFans Cookies")
    print("---------------------------------------")

    print("Checking clipboard...")
    raw_text = get_clipboard_content()
    
    extracted = parse_smart(raw_text)
    
    has_headers = False
    if extracted.get("user-agent") or extracted.get("cookie") or "sess=" in raw_text:
        has_headers = True

    if not has_headers:
        print("\nERROR: No Headers found!")
        print("Please copy the 'onlyfans.com/api2/v2/lists?filter=chat' section from DevTools.")
        time.sleep(3)
        return

    cookies = parse_cookies(extracted.get("cookie", ""))
    
    if not extracted.get("user-agent") and not cookies.get("sess"):
        print("\nData looks incomplete (Missing UA or Session). Aborting.")
        time.sleep(2)
        return

    print("Data looks valid. Processing...")

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
    else:
        print("⚠️ Warning: Neither Auth.json nor Auth.json.example found. Creating from scratch.")

    auth_update = {
        "user-agent": extracted.get("user-agent", current_auth.get("user-agent", "")),
        "user-id": extracted.get("user-id", cookies.get("auth_id", current_auth.get("user-id", ""))),
        "x-bc": extracted.get("x-bc", cookies.get("fp", current_auth.get("x-bc", ""))),
        "x-hash": extracted.get("x-hash", current_auth.get("x-hash", "")),
        "x-of-rev": extracted.get("x-of-rev", "202602012155-7f8fb7678a"),
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
        print(f"\n✅ Success! Updated: {auth_file}")
    except Exception as e:
        print(f"Error saving file: {e}")

    print("Bye.")
    time.sleep(1.5)

if __name__ == "__main__":
    main()