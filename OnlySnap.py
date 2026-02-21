#!/usr/bin/env python3
import re
import os
import sys
import subprocess
import json
import shutil
import requests
import time
import datetime as dt
import hashlib
import traceback
import datetime
import ctypes
import platform
import argparse
import threading
import base64
import logging
import asyncio
from datetime import date
from concurrent.futures import ThreadPoolExecutor, as_completed
from colorama import init, Fore, Style
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Button, DataTable, Label, ProgressBar, Log, Static, Input, Select
from textual import on, work
from textual.screen import Screen
from textual.containers import Grid
from pywidevine.pssh import PSSH

system = platform.system()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DMR_DIR = os.path.join(BASE_DIR, "dmr")
CURRENT_VERSION = "1.0.1"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/jordon31/OnlySnap/main/OnlySnap.py"

if system == "Windows":
    ffmpeg_fname = "ffmpeg.exe"
    downloader_fname = "N_m3u8DL-RE.exe"
    mp4decrypt_fname = "mp4decrypt.exe"
else: # linux/mac
    ffmpeg_fname = "ffmpeg"
    downloader_fname = "N_m3u8DL-RE"
    mp4decrypt_fname = "mp4decrypt"

local_ffmpeg = os.path.join(DMR_DIR, ffmpeg_fname)
local_downloader = os.path.join(DMR_DIR, downloader_fname)
local_mp4decrypt = os.path.join(DMR_DIR, mp4decrypt_fname)

if os.path.isfile(local_ffmpeg):
    FFMPEG_EXE = local_ffmpeg
else:
    FFMPEG_EXE = ffmpeg_fname

if os.path.isfile(local_downloader):
    DOWNLOADER_EXE = local_downloader
else:
    DOWNLOADER_EXE = downloader_fname

if os.path.isfile(local_mp4decrypt):
    MP4DECRYPT_EXE = local_mp4decrypt
else:
    MP4DECRYPT_EXE = mp4decrypt_fname

if system != "Windows":
    try:
        if os.path.isfile(local_ffmpeg): os.chmod(local_ffmpeg, 0o755)
        if os.path.isfile(local_downloader): os.chmod(local_downloader, 0o755)
        if os.path.isfile(local_mp4decrypt): os.chmod(local_mp4decrypt, 0o755)
    except: pass

class DownloadManager:
    def __init__(self, log_func, clear_func=None):
        self.log = log_func
        self.clear_log = clear_func
        self.stop_requested = False

    def run_mass_download(self, username, progress_callback):
        global PROFILE, PROFILE_ID, PROFILE_INFO, new_files
        try:
            clean_username = username.replace("@", "").strip()
            config = load_config()
            
            # Settings
            disable_cover_highlights = config['settings']['disable_cover_highlights']
            disable_download_txt = config['settings']['disable_download_post_with_txt']
            download_tagged = config['settings']['download_tagged_posts']
            download_labels_option = config['settings'].get('download_labels', False)
            merge_tagged = config['settings']['merge_tagged_media']
            
            PROFILE_INFO = get_user_info(clean_username)
            PROFILE = PROFILE_INFO['username']
            PROFILE_ID = str(PROFILE_INFO["id"])
            new_files = 0
            
            assure_dir("Profiles/" + PROFILE)
            assure_dir("Profiles/" + PROFILE + "/Public")
            
            # Dump info
            sinf = {
                "id": PROFILE_INFO["id"],
                "name": PROFILE_INFO["name"],
                "username": PROFILE_INFO["username"],
                "about": PROFILE_INFO.get("about"),
                "joinDate": PROFILE_INFO.get("joinDate"),
                "website": PROFILE_INFO.get("website")
            }
            try: sinf["joinDate"] = datetime.datetime.strptime(sinf["joinDate"], "%Y-%m-%dT%H:%M:%S+00:00").strftime("%Y-%m-%d")
            except: pass
            with open(f"Profiles/{PROFILE}/Dump.json", 'w', encoding='utf-8') as f:
                json.dump(sinf, f, ensure_ascii=False, indent=4)

            check_and_update_profile_cache(PROFILE_ID)
            download_public_files()
            count_public = new_files 

            stories_list = []
            if not self.stop_requested:
                res = get_all_stories()
                if isinstance(res, dict) and 'list' in res: stories_list = res['list']
                elif isinstance(res, list): stories_list = res
                stories_list = [s for s in stories_list if isinstance(s, dict)]

            highlights_list = []
            if not self.stop_requested:
                res = get_all_highlights()
                if isinstance(res, dict) and 'list' in res: highlights_list = res['list']
                elif isinstance(res, list): highlights_list = res
                highlights_list = [h for h in highlights_list if isinstance(h, dict)]

            chats_list = []
            if not self.stop_requested:
                chats_list = get_all_chats() or []
                chats_list = [c for c in chats_list if isinstance(c, dict)]

            # Posts Retrieval
            photo_posts = read_from_cache(PROFILE_ID, "photos") or []
            if not photo_posts: 
                raw = api_request(f"/users/{PROFILE_ID}/posts/photos", getdata={"limit": "999999"})
                photo_posts = get_all_photos(raw)
                update_profile_cache(PROFILE_ID, "photos", photo_posts)
            
            video_posts = read_from_cache(PROFILE_ID, "videos") or []
            if not video_posts:
                raw = api_request(f"/users/{PROFILE_ID}/posts/videos", getdata={"limit": "999999"})
                video_posts = get_all_videos(raw)
                update_profile_cache(PROFILE_ID, "videos", video_posts)

            archived_posts = read_from_cache(PROFILE_ID, "archived") or []
            if not archived_posts:
                raw = api_request(f"/users/{PROFILE_ID}/posts/archived", getdata={"limit": "999999"})
                archived_posts = get_all_archived(raw)
                update_profile_cache(PROFILE_ID, "archived", archived_posts)
            
            stream_posts = read_from_cache(PROFILE_ID, "streams") or []
            if not stream_posts:
                raw = api_request(f"/users/{PROFILE_ID}/posts/streams", getdata={"limit": "999999"})
                stream_posts = get_all_streams(raw)
                update_profile_cache(PROFILE_ID, "streams", stream_posts)

            seen_post_ids = set()
            unique_counts = { 'archived': 0, 'stream': 0, 'video': 0, 'photo': 0 }
            skipped_ads_count = 0
            final_download_list = [] 

            prioritized_lists = [
                (archived_posts, 'archived'),
                (stream_posts, 'stream'),
                (video_posts, 'video'),
                (photo_posts, 'photo')
            ]

            for current_list, category in prioritized_lists:
                if not current_list: continue
                for post in current_list:
                    if not isinstance(post, dict): continue
                    if not post.get("canViewMedia", True): continue

                    pid = str(post.get("id"))
                    if pid in seen_post_ids: continue 
                    
                    text = post.get("text") or ""
                    tags = ["#adv", "#ad", "#advertising", "#ad24", "#ads", "spin", "#Advertisement"]
                    is_spam = any(tag in (text.lower() if text else "") for tag in tags)
                    
                    if is_spam and not download_tagged:
                        skipped_ads_count += 1
                        seen_post_ids.add(pid) 
                        continue

                    media_count = len(post.get("media", []))
                    if media_count > 0:
                        seen_post_ids.add(pid) 
                        unique_counts[category] += media_count 
                        is_arch = (category == 'archived')
                        is_str = (category == 'stream')
                        final_download_list.append((post, is_arch, is_str))

            c_stories = 0
            for s in stories_list:
                if s.get("canView", True): c_stories += len(s.get('media', []))
            
            c_chats = 0
            for c in chats_list:
                if c.get("canView", True): c_chats += len(c.get('media', []))

            c_highlights_files = 0
            c_highlights_covers = 0
            if not disable_cover_highlights: c_highlights_covers = len(highlights_list)
            
            if highlights_list:
                self.log(f"...Analyzing Highlights (Please wait)...")
                for h_folder in highlights_list:
                    hid = h_folder.get("id")
                    if hid:
                        try:
                            details = get_highlight_details_API(hid)
                            if isinstance(details, dict):
                                h_stories = details.get("stories", [])
                                for s in h_stories:
                                    if s.get("canView", True): 
                                        c_highlights_files += len(s.get("media", []))
                        except: pass

            total_post_files = sum(unique_counts.values())
            total_global_files = total_post_files + c_stories + c_chats + c_highlights_files + c_highlights_covers + count_public

            if self.clear_log: self.clear_log()
            
            if total_global_files == 0:
                self.log(f"Profile @{PROFILE} has no content available.")
                progress_callback(100, 100, "No content")
                return

            self.log(f"--- Report for @{PROFILE} ---")
            if unique_counts['photo'] > 0:    self.log(f"PHOTOS: {unique_counts['photo']}")
            if unique_counts['video'] > 0:    self.log(f"VIDEOS: {unique_counts['video']}")
            if unique_counts['stream'] > 0:   self.log(f"STREAMS: {unique_counts['stream']}")
            if unique_counts['archived'] > 0: self.log(f"ARCHIVED: {unique_counts['archived']}")
            if c_stories > 0:  self.log(f"STORIES: {c_stories}")
            if c_chats > 0:    self.log(f"MESSAGES: {c_chats}")
            
            if c_highlights_files > 0 or c_highlights_covers > 0:
                hl_msg = f"HIGHLIGHTS: {c_highlights_files}"
                if c_highlights_covers > 0: hl_msg += f" (+ {c_highlights_covers} Covers)"
                self.log(hl_msg)

            if count_public > 0: self.log(f"PUBLIC FILES: {count_public} (Avatar/Header)")

            self.log("--------------------------------")
            self.log(f"Found {total_global_files} total files.")
            if skipped_ads_count > 0: self.log(f"Skipped {skipped_ads_count} SPAM/AD posts.")
            self.log("--------------------------------")
            
            if download_labels_option:
                self.log(f"--> Starting Labels...") 
            else:
                self.log(f"--> Starting download sync...") 

            if not disable_download_txt:
                assure_dir(f"Profiles/{PROFILE}/Media")

            self.current_file_progress = count_public
            
            def on_file_dl():
                self.current_file_progress += 1
                curr = min(self.current_file_progress, total_global_files)
                progress_callback(curr, total_global_files, f"Downloading @{PROFILE}")

            if count_public > 0:
                progress_callback(count_public, total_global_files, f"Downloading @{PROFILE}")
            label_map = {} 
            
            if download_labels_option and not self.stop_requested:
                labels_list = get_all_labels()
                
                if labels_list:
                    for label in labels_list:
                        if self.stop_requested: break
                        lid = label.get("id")
                        lname = clean_filename(label.get("name", f"Label_{lid}")).strip()
                        if label.get("postsCount", 0) == 0: continue

                        l_posts = get_posts_from_label(lid)
                        if not l_posts: continue

                        # Check
                        has_vid = False
                        has_pic = False
                        for lp in l_posts:
                            if not lp.get("canViewMedia", True): continue
                            for m in lp.get("media", []):
                                if m['type'] == 'photo': has_pic = True
                                elif m['type'] in ['video', 'gif']: has_vid = True
                        
                        is_mixed = has_vid and has_pic
                        base_label_path = f"Profiles/{PROFILE}/Media/Labels/{lname}/"

                        for lp in l_posts:
                            pid = str(lp.get("id"))
                            label_map[pid] = {
                                "base": base_label_path,
                                "mixed": is_mixed
                            }

            with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
                futures = []

                # A. CHATS
                if chats_list:
                    cp = f"Profiles/{PROFILE}/Media/Chat/Photos/"
                    cv = f"Profiles/{PROFILE}/Media/Chat/Videos/"
                    for chat in chats_list:
                        for media in chat.get("media", []):
                            src = media.get("files", {}).get("full", {}).get("url")
                            if src:
                                p = cv if media['type'] == 'video' else cp
                                futures.append(executor.submit(download_media, media, False, path=p, source_url=src))

                # B. STORIES
                if stories_list:
                    for story in stories_list:
                        for media in story.get("media", []):
                            src = media.get("files", {}).get("full", {}).get("url")
                            if src:
                                futures.append(executor.submit(download_media, media, False, path=f"Profiles/{PROFILE}/Media/Stories/", source_url=src))

                # C. HIGHLIGHTS 
                if highlights_list:
                    download_highlights({"list": highlights_list}, file_callback=on_file_dl)

                # D. POSTS (STANDARD + LABEL OVERRIDE)
                for post, is_arch, is_str in final_download_list:
                    if self.stop_requested: break
                    
                    pid = str(post.get("id"))
                    text = post.get("text") or ""
                    
                    post_ts_unix = float(post.get("postedAtPrecise", time.time()))
                    post_date = dt.datetime.fromtimestamp(post_ts_unix)
                    post_date_str = post_date.strftime('%Y-%m-%dT%H_%M_%S')

                    contains_tags = any(tag in (text.lower()) for tag in ["#adv", "#ad", "spin", "Advertisement"])        
                    path_override = None
                    is_in_label = False

                    # Check Tagged
                    if download_tagged and contains_tags:
                        base_tag = f"Profiles/{PROFILE}/Media/Tag-Post"
                        if merge_tagged: path_override = f"/{base_tag}/"
                        else: path_override = "TAG_SPLIT"
                    
                    # Check Label (if active via settings)
                    elif pid in label_map:
                        is_in_label = True
                        l_info = label_map[pid]
                        base_label = l_info['base']
                        if l_info['mixed']:
                            path_override = "LABEL_MIXED|" + base_label
                        else:
                            path_override = base_label

                    if not disable_download_txt and text:
                        txt_dir = None
                        if is_in_label:
                            txt_dir = label_map[pid]['base']
                        elif path_override == "TAG_SPLIT" or (download_tagged and contains_tags):
                             txt_dir = f"Profiles/{PROFILE}/Media/Posts/{post_date_str}"
                        elif path_override is None: # Standard Post
                             txt_dir = f"Profiles/{PROFILE}/Media/Posts/{post_date_str}"
                        
                        if txt_dir:
                            assure_dir(txt_dir)
                            with open(f"{txt_dir}/_text.txt", "w", encoding='utf-8') as f: f.write(text)

                    for media in post.get("media", []):
                        current_media_path = None
                        
                        if path_override == "TAG_SPLIT":
                            current_media_path = f"/Profiles/{PROFILE}/Media/Tag-Post/{media['type']}s/"
                        elif path_override and path_override.startswith("LABEL_MIXED|"):
                            real_base = path_override.split("|")[1]
                            if media['type'] == 'photo': current_media_path = real_base + "Photos/"
                            elif media['type'] in ['video', 'gif']: current_media_path = real_base + "Videos/"
                            else: current_media_path = real_base
                        else:
                            current_media_path = path_override         
                        # URL & DRM
                        source_url = None
                        files = media.get("files", {})
                        cf_cookies = None
                        if "drm" in files and files["drm"]:
                            source_url = files["drm"].get("manifest", {}).get("dash")
                            signature = files["drm"].get("signature", {}).get("dash", {})
                            if signature:
                                p = signature.get("CloudFront-Policy")
                                s = signature.get("CloudFront-Signature")
                                k = signature.get("CloudFront-Key-Pair-Id")
                                if p and s and k: cf_cookies = f"CloudFront-Policy={p}; CloudFront-Signature={s}; CloudFront-Key-Pair-Id={k}"
                        if not source_url:
                            source_url = files.get("source", {}).get("url") or files.get("full", {}).get("url")

                        if source_url:
                            futures.append(executor.submit(
                                download_media, 
                                media, 
                                is_arch, 
                                current_media_path,
                                post_date, 
                                is_str, 
                                source_url, 
                                pid, 
                                cf_cookies
                            ))

                for f in as_completed(futures):
                    try:
                        if f.result(): 
                            new_files += 1
                            on_file_dl()
                    except: pass

            # --- FINISH ---
            progress_callback(total_global_files, total_global_files, "Completed")

            self.log("------------------------------------------------")
            if new_files == 0:
                self.log(f"NO NEW FILES TO DOWNLOAD.")
                self.log(f"All {total_global_failes} files are already up to date.")
            else:
                self.log("SYNC COMPLETED.")
                self.log(f"- Total files scanned: {total_global_files}")
                self.log(f"- New files downloaded: {new_files}")
            self.log("------------------------------------------------")

        except Exception as e:
            self.log(f"CRITICAL ERROR: {str(e)}")
            traceback.print_exc()


class SettingsScreen(Screen):    
    BINDINGS = [("escape", "cancel", "Close")]
    CSS = """
    SettingsScreen {
        align: center middle;
        background: rgba(0,0,0,0.7);
    }
    
    #settings_container {
        width: 80%;
        height: 80%;
        background: #1f1d2e;
        border: heavy #c4a7e7;
        padding: 2;
        overflow-y: scroll;
    }
    
    .setting_label { color: #ebbcba; margin-top: 1; }
    Button#btn_save { background: #31748f; color: #e0def4; margin-top: 2; width: 100%; }
    Button#btn_cancel { background: #eb6f92; color: #e0def4; margin-top: 1; width: 100%; }
    """

    def compose(self) -> ComposeResult:
        config = load_config()
        s = config.get("settings", {})
        
        with Container(id="settings_container"):
            yield Label("SETTINGS EDITOR", classes="info_sub")
            
            # --- Boolean Options ---
            yield Label("Use Month Names (Jan, Feb...):", classes="setting_label")
            yield Select([("Yes", "true"), ("No", "false")], value=str(s.get("use_month_names")).lower(), id="use_month_names")

            yield Label("Use Month Numbers (01, 02...):", classes="setting_label")
            yield Select([("Yes", "true"), ("No", "false")], value=str(s.get("use_month_numbers")).lower(), id="use_month_numbers")

            yield Label("Disable Year Folders:", classes="setting_label")
            yield Select([("Yes", "true"), ("No", "false")], value=str(s.get("no_year_folders")).lower(), id="no_year_folders")

            yield Label("Skip Highlight Covers:", classes="setting_label")
            yield Select([("Yes", "true"), ("No", "false")], value=str(s.get("disable_cover_highlights")).lower(), id="disable_cover_highlights")

            yield Label("Flatten Highlights (No Folders):", classes="setting_label")
            yield Select([("Yes", "true"), ("No", "false")], value=str(s.get("disable_folder_highlights")).lower(), id="disable_folder_highlights")

            yield Label("Skip Text Files download posts w the written text:", classes="setting_label")
            yield Select([("Yes", "true"), ("No", "false")], value=str(s.get("disable_download_post_with_txt")).lower(), id="disable_download_post_with_txt")

            yield Label("Download Tagged Posts (Ads/Spam):", classes="setting_label")
            yield Select([("Yes", "true"), ("No", "false")], value=str(s.get("download_tagged_posts")).lower(), id="download_tagged_posts")

            yield Label("Merge Tagged Media (One Folder):", classes="setting_label")
            yield Select([("Yes", "true"), ("No", "false")], value=str(s.get("merge_tagged_media")).lower(), id="merge_tagged_media")
             
            yield Label("Download Labels (Custom Lists):", classes="setting_label")
            yield Select([("Yes", "true"), ("No", "false")], value=str(s.get("download_labels", False)).lower(), id="download_labels")

            # --- Integer Option ---
            yield Label("Download Threads (Speed):", classes="setting_label")
            yield Input(value=str(s.get("thread_workers_count", 5)), id="thread_workers_count")

            yield Button("SAVE SETTINGS", id="btn_save")
            yield Button("EXIT", id="btn_cancel")

    @on(Button.Pressed, "#btn_save")
    def action_save(self):
        config = load_config()
        s = config["settings"]

        # Update boolean values
        s["use_month_names"] = self.query_one("#use_month_names").value == "true"
        s["use_month_numbers"] = self.query_one("#use_month_numbers").value == "true"
        s["no_year_folders"] = self.query_one("#no_year_folders").value == "true"
        s["disable_cover_highlights"] = self.query_one("#disable_cover_highlights").value == "true"
        s["disable_folder_highlights"] = self.query_one("#disable_folder_highlights").value == "true"
        s["disable_download_post_with_txt"] = self.query_one("#disable_download_post_with_txt").value == "true"
        s["download_tagged_posts"] = self.query_one("#download_tagged_posts").value == "true"
        s["merge_tagged_media"] = self.query_one("#merge_tagged_media").value == "true"
        s["download_labels"] = self.query_one("#download_labels").value == "true"

        # Update integer value
        try:
            val = int(self.query_one("#thread_workers_count").value)
            s["thread_workers_count"] = val
        except:
            pass

        save_config(config)
        self.app.pop_screen()
        self.app.query_one(Log).write_line("[*] Settings updated successfully.")

    @on(Button.Pressed, "#btn_cancel")
    def action_cancel(self):
        self.app.pop_screen()
        
class OnlySnapTUI(App):
    CSS = """
    Screen { 
        layout: horizontal; 
        background: #191724; 
        color: #e0def4; 
    }

    #sidebar { 
        width: 35%; 
        background: #1f1d2e; 
        border-right: heavy #ebbcba; 
        padding: 1; 
    }

    .info_sub { color: #f6c177; text-style: bold; margin: 1 0; }
    Input, Select { border: solid #c4a7e7; background: #26233a; color: #e0def4; }
    DataTable { height: 1fr; border: none; background: #1f1d2e; color: #9ccfd8; }

    #main_panel { width: 65%; padding: 1; height: 100%; }
    
    #info_box { 
        background: #26233a; 
        border: solid #c4a7e7; 
        padding: 1; 
        height: auto; 
    }

    #lbl_user { color: #ebbcba; text-style: bold; }
    #lbl_status { color: #9ccfd8; }

    ProgressBar { 
        width: 100%; 
        height: 3; 
        margin: 1 0; 
        color: #ebbcba;
        background: #191724;
    }

    #buttons_container { height: auto; margin-bottom: 1; }
    #buttons_container > Button { width: 1fr; margin-right: 1; }
    
    #btn_refresh { width: 100%; background: #c4a7e7; color: #191724; margin-top: 1; }
    #btn_dl { background: #31748f; color: #e0def4; }
    #btn_stop { background: #eb6f92; color: #e0def4; margin-right: 0; }

    Log { 
        width: 100%; 
        height: 1fr; 
        min-height: 20; 
        border: solid #ebbcba; 
        background: #191724;   
        overflow-y: scroll;
        scrollbar-color: #ebbcba #191724;
    }
    """

    def compose(self) -> ComposeResult:
        with Container(id="sidebar"):
            yield Label("SEARCH CREATOR", classes="info_sub")
            yield Input(placeholder="Type a name...", id="search_input")
            yield Label("FILTER BY TYPE", classes="info_sub")
            yield Select([("All", "all"), ("Paid", "Paid"), ("Free", "Free"), ("Trial", "Trial")], value="all", id="filter_type")
            yield DataTable(id="users_table")
            yield Button("Refresh List", id="btn_refresh")
            yield Button("Settings", id="btn_settings")
        with Container(id="main_panel"):
            with Vertical(id="info_box"):
                yield Label("Select a creator from the list", id="lbl_user")
                yield Label("Status: Waiting", id="lbl_status")
            
            yield ProgressBar(total=100, show_eta=True, id="progress_bar")
            
            with Horizontal(id="buttons_container"):
                yield Button("START DOWNLOAD", id="btn_dl", disabled=True)
                yield Button("STOP", id="btn_stop", disabled=True)
            
            yield Log(id="log_console")
        
        yield Footer()

    def on_mount(self):
        self.title = f"OnlySnap TUI v{CURRENT_VERSION} (Rose-Pine)"
        self.all_subs = []
        table = self.query_one(DataTable)
        table.cursor_type = "row"
        table.add_columns("Username", "Type")
        self.refresh_list()
        self.run_worker(self.check_updates, thread=True)

    def log_msg(self, text):
        try:
            log_widget = self.query_one(Log)
            if self._thread_id == threading.get_ident():
                log_widget.write_line(f"[*] {text}")
            else:
                self.call_from_thread(log_widget.write_line, f"[*] {text}")
        except: pass

    def clear_log_console(self):
        self.call_from_thread(self.query_one(Log).clear)

    @work(exclusive=True)
    async def refresh_list(self):
        self.log_msg("Syncing subscriptions...")
        try:
            cached_data = load_from_cache()
            old_users = set()
            if cached_data:
                old_users = {sub.get('username') for sub in cached_data}

            self.all_subs = fetch_and_cache_subs() 
            self.update_table()
            
            new_users = {sub.get('username') for sub in self.all_subs}
            
            if old_users != new_users:
                self.log_msg(f"Synced {len(self.all_subs)} creators (Cache Updated).")
            else:
                self.log_msg(f"Synced {len(self.all_subs)} creators.")
                
        except Exception as e:
            self.log_msg(f"Update error: {e}")

    def update_table(self):
        table = self.query_one(DataTable)
        search = self.query_one("#search_input").value.lower()
        t_filter = self.query_one("#filter_type").value
        table.clear()
        for sub in self.all_subs:
            u = sub.get('username', '').lower()
            t = sub.get('type', 'Paid')
            if (search in u) and (t_filter == "all" or t_filter == t):
                table.add_row(sub['username'], t, key=sub['username'])
    
    def check_updates(self):
        try:
            self.log_msg(f"Checking for updates (Current: v{CURRENT_VERSION})...")
            response = requests.get(GITHUB_RAW_URL, timeout=5)
            
            if response.status_code == 200:
                match = re.search(r'CURRENT_VERSION\s*=\s*[\'"]([^\'"]+)[\'"]', response.text)
                
                if match:
                    remote_version = match.group(1)
                    if remote_version != CURRENT_VERSION:
                        self.log_msg(f"[!] NEW UPDATE AVAILABLE: v{remote_version}")
                        self.log_msg(f"[!] Download at: https://github.com/jordon31/OnlySnap")
                        self.query_one("#lbl_status").update(f"Update Available: v{remote_version}!")
                    else:
                        self.log_msg("You have the latest version.")
                else:
                    self.log_msg("Could not verify remote version.")
            else:
                self.log_msg("Failed to connect to GitHub.")
        except Exception as e:
            pass

    @on(Input.Changed, "#search_input")
    def on_search(self): self.update_table()

    @on(Select.Changed, "#filter_type")
    def on_filter_change(self): self.update_table()

    @on(DataTable.RowSelected)
    def user_selected(self, event):
        self.query_one(ProgressBar).update(total=100, progress=0)
        self.query_one("#lbl_status").update("Status: Waiting")
        self.query_one(Log).clear()
        self.selected_username = event.row_key.value
        self.query_one("#lbl_user").update(f"Target: @{self.selected_username}")
        self.query_one("#btn_dl").disabled = False
        self.log_msg(f"Selected: {self.selected_username}")

    @on(Button.Pressed, "#btn_dl")
    def start_dl(self):
        self.query_one(Log).clear()
        self.query_one("#btn_dl").disabled = True    
        self.query_one("#btn_stop").disabled = False  
        self.query_one("#btn_refresh").disabled = True
        self.query_one("#search_input").disabled = True
        self.query_one("#filter_type").disabled = True
        self.query_one("#users_table").disabled = True 
        
        self.query_one("#lbl_status").update("Status: Analyzing...")
        
        self.downloader = DownloadManager(self.log_msg, self.clear_log_console)
        self.run_worker(self.download_task, thread=True)
    @on(Button.Pressed, "#btn_refresh")
    async def action_refresh(self): 
        await asyncio.sleep(0.1) 
        self.query_one(Log).clear()
        self.refresh_list()

    @on(Button.Pressed, "#btn_settings")
    def open_settings(self):
        self.push_screen(SettingsScreen())

    def download_task(self):
        try:
            def update_ui(curr, total, msg):
                self.call_from_thread(self.update_progress, curr, total, msg)
            self.downloader.run_mass_download(self.selected_username, update_ui)
        except Exception as e:
            self.log_msg(f"Error: {e}")
        finally:
            self.call_from_thread(self.reset_ui)

    def update_progress(self, curr, total, msg):
        # Calculate percentage
        if total > 0:
            pct = int((curr / total) * 100)
        else:
            pct = 0
            
        self.query_one(ProgressBar).update(total=total, progress=curr)
        self.query_one("#lbl_status").update(f"{msg} - Files: {curr}/{total} ({pct}%)")

    def reset_ui(self):
        self.query_one("#btn_dl").disabled = False
        self.query_one("#btn_stop").disabled = True
        
        # Re-enable interaction
        self.query_one("#btn_refresh").disabled = False
        self.query_one("#search_input").disabled = False
        self.query_one("#filter_type").disabled = False
        self.query_one("#users_table").disabled = False

        if hasattr(self, 'downloader') and self.downloader.stop_requested:
            self.query_one("#lbl_status").update("Status: Stopped by user")
        else:
            self.query_one("#lbl_status").update("Status: Completed")

    @on(Button.Pressed, "#btn_stop")
    def request_stop(self):
        if hasattr(self, 'downloader'):
            self.downloader.stop_requested = True
            self.log_msg("Stopping requested...")

#logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
#logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

if system == "Windows":
    ctypes.windll.kernel32.SetConsoleTitleW("OnlySnap") #Title Application Windows
elif system == "Darwin":
    sys.stdout.write(f"\x1b]2;{'OnlySnap'}\x07") #Title Application MAC
    sys.stdout.flush()
else:
    sys.stdout.write(f"\033]0;{'OnlySnap'}\a") #Title Application Linux
    sys.stdout.flush()

# api info
URL = "https://onlyfans.com"
API_URL = "/api2/v2"
APP_TOKEN = "33d57ade8c02dbc5a333db99ff9ae26a"

# user info from /users/customer
USER_INFO = {}

# target profile
PROFILE = ""
# profile data from /users/<profile>
PROFILE_INFO = {}
PROFILE_ID = ""

def clean_up_empty_folder(folder_path):
    try:
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            if not os.listdir(folder_path):
                os.rmdir(folder_path)
    except Exception:
        pass

def assure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def create_auth():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    auth_file_path = os.path.join(current_dir, "Configs", "OnlyFans", "Auth.json")

    with open(auth_file_path) as f:
        ljson = json.load(f)

    cookies = {
        "sess": ljson.get("sess"),
        "auth_id": ljson.get("user-id"),
        "st": ljson.get("st"),
        "lang": "en",
        "fp": ljson.get("fp"),
        "__cf_bm": ljson.get("cf_bm"),
        "_cfuvid": ljson.get("cfuvid")
    }
    
    cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items() if v])

    return {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": ljson["user-agent"],
        "Accept-Encoding": "gzip, deflate",
        "user-id": ljson["user-id"],
        "x-bc": ljson["x-bc"],
        "x-of-rev": ljson.get("x-of-rev", ""),
        "x-hash": ljson.get("x-hash", ""),
        "Cookie": cookie_str,
        "app-token": APP_TOKEN,
    }

def save_config(config):
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "Configs", "OnlyFans", "Config.json")
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=4)

def load_config():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(current_dir, "Configs", "OnlyFans", "Config.json")
    with open(config_path) as f:
        config = json.load(f)
    return config

CONFIG = load_config()
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Cache")
CACHE_FILE = os.path.join(CACHE_DIR, "subs_cache.json")
NUM_THREADS = CONFIG['settings']['thread_workers_count']

def check_and_clear_cache_if_user_id_changed():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    user_id_cache_path = os.path.join(current_dir, "Configs", "OnlyFans", "user_id_cache.txt")
    auth_file_path = os.path.join(current_dir, "Configs", "OnlyFans", "Auth.json")

    with open(auth_file_path) as f:
        current_user_id = json.load(f)["user-id"]

    if not os.path.exists(user_id_cache_path):
        with open(user_id_cache_path, 'w') as f:
            f.write(current_user_id)
        return

    with open(user_id_cache_path, 'r') as f:
        cached_user_id = f.read().strip()

    if current_user_id != cached_user_id:
        if os.path.exists(CACHE_DIR):
            shutil.rmtree(CACHE_DIR)
        with open(user_id_cache_path, 'w') as f:
            f.write(current_user_id)

check_and_clear_cache_if_user_id_changed()

def convert_to_mp4(input_path):
    if not os.path.exists(input_path): return
    if input_path.endswith(".mp4"): return

    output_path = os.path.splitext(input_path)[0] + ".mp4"
    try:
        subprocess.run([FFMPEG_EXE, "-y", "-i", input_path, "-c", "copy", "-strict", "experimental", output_path],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            os.remove(input_path)
    except Exception:
        pass

def create_signed_headers(link, queryParams):
    global API_HEADER
    path = "/api2/v2" + link
    if queryParams:
        query = '&'.join('='.join((key, str(val))) for (key, val) in queryParams.items())
        path = f"{path}?{query}"

    unixtime = str(int(dt.datetime.now().timestamp()))
    msg = "\n".join([dynamic_rules["static_param"], unixtime, path, API_HEADER["user-id"]])
    message = msg.encode("utf-8")
    hash_object = hashlib.sha1(message)
    sha_1_sign = hash_object.hexdigest()
    sha_1_b = sha_1_sign.encode("ascii")
    checksum = sum([sha_1_b[number] for number in dynamic_rules["checksum_indexes"]]) + dynamic_rules["checksum_constant"]
    API_HEADER["sign"] = dynamic_rules["format"].format(sha_1_sign, abs(checksum))
    API_HEADER["time"] = unixtime
    API_HEADER["x-of-rev"] = dynamic_rules.get("x-of-rev", "") 
    API_HEADER["x-hash"] = dynamic_rules.get("x-hash", "") 

def api_request(endpoint, getdata=None, postdata=None, getparams=None):
    if getparams is None:
        getparams = {"order": "publish_date_desc"}
        
    if getdata is not None:
        for i in getdata:
            getparams[i] = getdata[i]

    if postdata is None:
        create_signed_headers(endpoint, getparams)
        response = requests.get(URL + API_URL + endpoint, headers=API_HEADER, params=getparams)
    else:
        create_signed_headers(endpoint, getparams)
        response = requests.post(URL + API_URL + endpoint, headers=API_HEADER, params=getparams, data=postdata)

    if endpoint == "/chats/" + PROFILE_ID + "/messages":
        return response.json()

    try:
        json_data = response.json()
    except:
        return response

    if isinstance(json_data, list) and getdata is not None:
        if str(getdata.get("limit")) == "999999":
            full_list = json_data
            
            while True:
                if not full_list: break
                
                last_post = full_list[-1]
                if "postedAtPrecise" not in last_post: break
                
                getparams['beforePublishTime'] = last_post['postedAtPrecise']
                
                create_signed_headers(endpoint, getparams)
                new_resp = requests.get(URL + API_URL + endpoint, headers=API_HEADER, params=getparams)
                
                try:
                    new_batch = new_resp.json()
                except: break
                
                if isinstance(new_batch, list) and len(new_batch) > 0:
                    full_list.extend(new_batch)
                else:
                    break
            
            return full_list

    return json_data

def get_highlight_details_API(highlight_id):
    endpoint = f"/stories/highlights/{highlight_id}"
    create_signed_headers(endpoint, {})
    
    response = api_request(endpoint)
    
    if hasattr(response, 'json'):
        return response.json()
    
    return response if isinstance(response, dict) else {}

# /users/<profile>
# get information about <profile>
# <profile> = "customer" -> info about yourself

def get_user_info(profile):
    if isinstance(profile, str) and profile.startswith("@"):
        profile = profile[1:]
    
    try:
        response = api_request("/users/" + profile)
        
        if hasattr(response, "status_code"):
            if response.status_code != 200:
                raise Exception(f"HTTP {response.status_code}: {response.reason}")
            info = response.json()
        else:
            info = response

        if isinstance(info, dict) and "error" in info:
            msg = info["error"].get("message", "Error API")
            raise Exception(msg)
            
        return info
    except Exception as e:
        err_msg = str(e) if str(e) else f"Generic Error {type(e).__name__}"
        raise Exception(err_msg)

# to get subscribesCount for displaying all subs
# info about yourself
def user_me():
    me = api_request("/users/me")
    
    if hasattr(me, 'json'):
        me = me.json()
        
    if "error" in me:
        print("\nERROR: " + me["error"]["message"])
        time.sleep(4)
        sys.exit()
    return me

def user_me_username():
    me = api_request("/users/me")
    
    if hasattr(me, 'json'):
        me = me.json()

    if "error" in me:
        print("\nERROR: " + me["error"]["message"])
        time.sleep(4)
        sys.exit()
    return me.get("username", "User")
    
def save_to_cache(data):
    assure_dir(CACHE_DIR)
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

def load_from_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

def get_subs_count_from_api():
    me = api_request("/users/me").json()
    return me.get("subscribesCount", 0)

def update_subs_cache_if_needed():
    current_subs_count = get_subs_count_from_api()
    cache_subs_count = load_subs_count_from_cache()
    
    if current_subs_count != cache_subs_count:
        print("Subscription update in progress...")
        total_subs = fetch_and_cache_subs()
        save_subs_count_to_cache(current_subs_count)
        os.system('cls' if os.name == 'nt' else 'clear')
        return total_subs
    else:
        return load_from_cache()

def load_subs_count_from_cache():
    subs_count_file = os.path.join(CACHE_DIR, "subs_count.json")
    if os.path.exists(subs_count_file):
        with open(subs_count_file, 'r') as f:
            return json.load(f).get("subscribesCount", 0)
    return 0

def save_subs_count_to_cache(subs_count):
    subs_count_file = os.path.join(CACHE_DIR, "subs_count.json")
    with open(subs_count_file, 'w') as f:
        json.dump({"subscribesCount": subs_count}, f)

def update_cache_if_subs_changed():
    user_info = api_request("/users/me").json()
    current_subs_count = user_info.get("subscribesCount", 0)
    
    cached_subs_count = load_subs_count_from_cache()
    
    if current_subs_count != cached_subs_count:
        print("Number of subscriptions changed. Updating cache in progress...")
        fetch_and_cache_subs()
        save_subs_count_to_cache(current_subs_count)
        os.system('cls' if os.name == 'nt' else 'clear')
    
def read_from_cache(profile_id, data_type):
    start_time = time.time()
    profile_cache_file = os.path.join(CACHE_DIR, f"profile_{profile_id}", f"cache_{profile_id}.json")
    if os.path.exists(profile_cache_file):
        with open(profile_cache_file, 'r') as f:
            cache_data = json.load(f)
            cached_value = cache_data.get(data_type)
            if cached_value:
                logging.debug(f"{data_type} data found in cache. Cache read time: {time.time() - start_time} seconds.")
            else:
                logging.debug(f"{data_type} data not found in cache.")
            return cached_value
    logging.debug(f"No cache file found for profile {profile_id}.")
    return None

def get_user_post_count(profile_id):
    logging.debug(f"Requesting user post count for profile ID: {profile_id}")
    user_data = api_request(f"/users/{profile_id}")
    
    if hasattr(user_data, 'json'):
        medias_count = user_data.json().get("mediasCount", 0)
    else:
        medias_count = user_data.get("mediasCount", 0)
        
    logging.debug(f"Retrieved post count for profile ID {profile_id}: {medias_count}")
    return medias_count

def check_and_update_profile_cache(profile_id): #new logic
    logging.debug(f"Checking profile cache for ID: {profile_id}")
    
    current_post_count = get_user_post_count(profile_id)
    cached_post_count = read_from_cache(profile_id, "post_count")
    
    logging.debug(f"Post counts - Current: {current_post_count} | Cached: {cached_post_count}")
    
    if cached_post_count is None:
        print(f"Cache missing. Downloading all {current_post_count} posts...")
        user_posts = api_request(f"/users/{profile_id}/posts", getdata={"limit": "999999"})
        update_profile_cache(profile_id, "posts", user_posts)
        update_profile_cache(profile_id, "post_count", current_post_count)
        return True

    if current_post_count != cached_post_count:
        diff = current_post_count - cached_post_count
        
        if diff > 0 and diff < 100:
            print(f"Quick Update: Downloading only {diff} new posts...")
            new_data = api_request(f"/users/{profile_id}/posts", getdata={"limit": str(diff + 5)})
            
            old_data = read_from_cache(profile_id, "posts") or []
            
            new_ids = {x['id'] for x in new_data}
            clean_old_data = [x for x in old_data if x['id'] not in new_ids]
            
            user_posts = new_data + clean_old_data
        else:
            print(f"Full Update: Downloading all {current_post_count} posts...")
            user_posts = api_request(f"/users/{profile_id}/posts", getdata={"limit": "999999"})

        update_profile_cache(profile_id, "posts", user_posts)
        update_profile_cache(profile_id, "post_count", current_post_count)
        return True
        
    logging.info("No new posts detected. Using existing cache.")
    return False

def update_profile_cache(profile_id, data_type, new_data):
    start_time = time.time()
    profile_cache_dir = os.path.join(CACHE_DIR, f"profile_{profile_id}")
    if not os.path.exists(profile_cache_dir):
        os.makedirs(profile_cache_dir)
    profile_cache_file = os.path.join(profile_cache_dir, f"cache_{profile_id}.json")
    
    if os.path.exists(profile_cache_file):
        with open(profile_cache_file, 'r') as f:
            cache_data = json.load(f)
    else:
        cache_data = {}
    
    cache_data[data_type] = new_data
    
    with open(profile_cache_file, 'w') as f:
        json.dump(cache_data, f, indent=4)
    logging.debug(f"Cache for {data_type} updated. Cache update time: {time.time() - start_time} seconds.")

def fetch_and_cache_subs():
    SUB_LIMIT = 10
    offset = 0
    total_subs = []
    
    while True:
        params = {
            "type": "active",
            "sort": "desc",
            "field": "expire_date",
            "limit": str(SUB_LIMIT),
            "offset": str(offset)
        }
        
        response = api_request("/subscriptions/subscribes", getparams=params)
        
        if hasattr(response, 'json'):
             try:
                 subscriptions = response.json()
             except:
                 subscriptions = []
        else:
             subscriptions = response

        if not subscriptions:
            break
            
        for sub in subscriptions:
            if 'currentSubscribePrice' in sub and sub['currentSubscribePrice'] == 0:
                sub['type'] = 'Free'
                if 'subscribedByData' in sub and 'subscribes' in sub['subscribedByData']:
                    for subscribe in sub['subscribedByData']['subscribes']:
                        if 'type' in subscribe and subscribe['type'] == 'trial':
                            sub['type'] = 'Trial'
            else:
                sub['type'] = 'Paid'
        
        total_subs.extend(subscriptions)
        offset += SUB_LIMIT
    
    save_to_cache(total_subs)
    return total_subs

new_files = 0

def set_file_mtime(file_path, timestamp):
    mod_time = time.mktime(timestamp.timetuple())
    os.utime(file_path, (mod_time, mod_time))

def download_public_files():
    public_files = ["avatar", "header"]
    for public_file in public_files:
        source = PROFILE_INFO[public_file]
        if source is None:
            continue
        id = get_id_from_path(source)
        file_type = re.findall(r"\.\w+", source)[-1]
        path = "/" + public_file + file_type
        full_path = "Profiles/" + PROFILE + "/Public" + path
        
        if not os.path.isfile(full_path):
            download_file(PROFILE_INFO[public_file], full_path)
            global new_files
            new_files += 1

# ==========================================
# DRM - START -- with API external by me
# ==========================================

def log_debug(msg):
    try:
        timestamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(DEBUG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {msg}\n")
    except:
        pass

def get_pssh_from_mpd(mpd_url, cookies_override=None):
    log_debug(f"--- Checking MPD: {mpd_url} ---")
    
    current_cookie = API_HEADER["Cookie"]
    if cookies_override:
        current_cookie = f"{current_cookie}; {cookies_override}"
    
    cdn_headers = {
        "User-Agent": API_HEADER["User-Agent"],
        "Cookie": current_cookie # Use correct cookies
    }

    try:
        r = requests.get(mpd_url, headers=cdn_headers)
        
        if r.status_code == 200:
            mpd_text = r.text
            
            # 1. Try standard Widevine tag
            psshs = re.findall(r'<(?:cenc:)?pssh>(.*)</(?:cenc:)?pssh>', mpd_text)
            for pssh_b64 in psshs:
                try:
                    cleaned_pssh = pssh_b64.replace(" ", "").replace("\n", "").replace("\r", "")
                    pssh_obj = PSSH(cleaned_pssh)
                    if pssh_obj.system_id.lower() == "edef8ba9-79d6-4ace-a3c8-27dcd51d21ed":
                        log_debug(f"FOUND PSSH (Widevine Tag): {cleaned_pssh}")
                        return cleaned_pssh
                except Exception:
                    continue

            # 2. Try generating from default_KID
            kid_match = re.search(r'cenc:default_KID="([0-9a-fA-F-]+)"', mpd_text)
            if kid_match:
                kid_str = kid_match.group(1).replace("-", "")
                log_debug(f"FOUND KID: {kid_str} (Manual PSSH gen)")
                try:
                    kid_bytes = bytes.fromhex(kid_str)
                    wv_system_id = bytes.fromhex("edef8ba979d64acea3c827dcd51d21ed")
                    pssh_data = b'\x12\x10' + kid_bytes
                    data_len = len(pssh_data).to_bytes(4, 'big')
                    box = b'pssh' + b'\x00\x00\x00\x00' + wv_system_id + data_len + pssh_data
                    total_len = (len(box) + 4).to_bytes(4, 'big')
                    gen_pssh = base64.b64encode(total_len + box).decode('utf-8')
                    log_debug(f"PSSH GENERATED: {gen_pssh}")
                    return gen_pssh
                except Exception as e:
                    log_debug(f"ERROR generating PSSH from KID: {e}")

            log_debug("FAILED: No PSSH or KID found in MPD.")
        else:
            log_debug(f"ERROR DOWNLOADING MPD: Status Code {r.status_code}")
            
    except Exception as e:
        log_debug(f"EXCEPTION REQUESTING MPD: {e}")
        
    return None

def get_widevine_keys(pssh_b64, media_id, post_id, cookies_override=None):
    SERVER_API_URL = "https://asdojknasdohjsadjon.online/api/get_keys"

    try:
        base_cookies = API_HEADER["Cookie"]
        if cookies_override:
            final_cookies = base_cookies
            if not final_cookies.endswith(";"): final_cookies += ";"
            final_cookies += " " + cookies_override
        else:
            final_cookies = base_cookies

        payload = {
            "pssh": pssh_b64,
            "media_id": str(media_id),
            "post_id": str(post_id),
            "user_id": str(API_HEADER["user-id"]),
            "user_agent": API_HEADER["User-Agent"],
            "x_bc": API_HEADER.get("x-bc", ""),
            "cookie": final_cookies
        }
        
        req = requests.post(SERVER_API_URL, json=payload, timeout=20)
        
        if req.status_code == 200:
            keys = req.json().get("keys")
            if not keys: return None
            return keys
        else:
            return None
    except:
        return None

def get_fresh_drm_data(post_id, media_id):
    try:
        post_data = api_request(f"/posts/{post_id}")
        
        if not post_data or "error" in post_data:
            return None

        media_list = post_data.get('media', [])
        for m in media_list:
            if str(m.get('id')) == str(media_id):
                return m.get('files', {}).get('drm')
                
    except Exception:
        pass
        
    return None

def download_drm_video(mpd_url, output_path, output_name, post_id, cookies_override=None):
    save_dir = os.path.dirname(output_path)
    assure_dir(save_dir)

    clean_name = re.sub(r'[<>:"/\\|?*]', '', output_name)

    temp_dir = os.path.join(save_dir, f"temp_dl_{clean_name}")
    if os.path.exists(temp_dir):
        try: shutil.rmtree(temp_dir)
        except: pass
    
    # Get PSSH from MPD
    pssh = get_pssh_from_mpd(mpd_url, cookies_override)
    keys = None
    
    # Check server for keys
    if pssh and post_id:
        keys = get_widevine_keys(pssh, clean_name, post_id, cookies_override)
    elif not post_id:
        log_debug("ERROR: Missing Post ID")

    cmd = [
        DOWNLOADER_EXE, 
        mpd_url,
        "--save-dir", save_dir,
        "--save-name", clean_name,
        "--tmp-dir", temp_dir,
        "--del-after-done",
        "--auto-select",
        "-M", "format=mp4",
        "--log-level", "OFF"
    ]

    if keys:
        for k in keys.split():
            cmd.extend(["--key", k])
    else:
        log_debug("WARNING: Downloading WITHOUT keys (File will be encrypted)")

    cmd.extend(["-H", f"User-Agent: {API_HEADER['User-Agent']}"])
    
    dl_cookie = API_HEADER["Cookie"]
    if cookies_override:
        dl_cookie = f"{dl_cookie}; {cookies_override}"
        
    cmd.extend(["-H", f"Cookie: {dl_cookie}"])
    
    try:
        process = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return process.returncode == 0
    except Exception as e:
        log_debug(f"Subprocess exception: {e}")
        return False

# ==========================================
# END DRM
# ==========================================

def get_year_folder(timestamp, media_type):
    config_path = os.path.join('Configs', 'OnlyFans', 'Config.json')
    with open(config_path, 'r') as f:
        settings = json.load(f)

    if settings['settings']['no_year_folders']:
        folder_name = ""
    else:
        today = dt.date.today()
        yesterday = today - dt.timedelta(days=1)
        last_week_limit = today - dt.timedelta(days=7)
        
        post_date = timestamp.date()
        
        if post_date == today:
            folder_name = "Today"
        elif post_date == yesterday:
            folder_name = "Yesterday"
        elif post_date > last_week_limit:
            folder_name = "Last Week"
        else:
            year = timestamp.year
            if settings['settings']['use_month_names']:
                month_name = timestamp.strftime("%B")
                folder_name = f"{year}/{month_name}"
            elif settings['settings']['use_month_numbers']:
                month_name = timestamp.strftime("%m")
                folder_name = f"{year}/{month_name}"
            else:
                folder_name = f"{year}"

    base_path = "Profiles/" + PROFILE + "/Media"
    
    if media_type == "photo":
        full_dest_path = base_path + "/!Photos/" + folder_name
        assure_dir(full_dest_path)
    elif media_type == "video":
        full_dest_path = base_path + "/!Videos/" + folder_name
        assure_dir(full_dest_path)

    return folder_name

def get_year_path(post_date):
    post_year = post_date.year
    folder_prefix = str(post_year)
    return folder_prefix

# download a media item and save it to the relevant directory
def download_media(media, is_archived, path=None, timestamp=None, is_stream=False, source_url=None, post_id=None, specific_cookies=None):
    global new_files
    id_str = str(media["id"])
    source = source_url if source_url else media.get("source", {}).get("source")

    if (media["type"] != "photo" and media["type"] != "video" and media["type"] != "gif") or not media['canView']:
        return False

    is_drm = ".mpd" in source if source else False
    
    if is_drm and post_id:
        fresh_drm = get_fresh_drm_data(post_id, media['id'])
        if fresh_drm:
            new_manifest = fresh_drm.get("manifest", {}).get("dash")
            if new_manifest:
                source = new_manifest
            
            sig = fresh_drm.get("signature", {}).get("dash", {})
            if sig:
                p = sig.get("CloudFront-Policy")
                s = sig.get("CloudFront-Signature")
                k = sig.get("CloudFront-Key-Pair-Id")
                if p and s and k:
                    specific_cookies = f"CloudFront-Policy={p}; CloudFront-Signature={s}; CloudFront-Key-Pair-Id={k}"

    if is_drm or media["type"] == "video" or media["type"] == "gif":
        ext = ".mp4"
    else:
        ext_match = re.findall(r'\.\w+\?', source) if source else []
        ext = ext_match[0][:-1] if ext_match else ".jpg"

    folder_name = "" 
    type_f = ""      

    if path is None:
        if is_stream:
            final_path = f"Profiles/{PROFILE}/Media/Streams/{id_str}{ext}"
        elif is_archived:
            sub_folder = "Photos" if media["type"] == "photo" else "Videos"
            final_path = f"Profiles/{PROFILE}/Media/Archived/{sub_folder}/{id_str}{ext}"
        else:
            folder_name = get_year_folder(timestamp, "photo" if media["type"] == "photo" else "video")
            type_f = "!Photos" if media["type"] == "photo" else "!Videos"
            final_path = f"Profiles/{PROFILE}/Media/{type_f}/{folder_name}/{id_str}{ext}"
    else:
        if path.startswith("/"):
            final_path = f"Profiles/{PROFILE}{path}{id_str}{ext}"
        else:
            final_path = f"{path}{id_str}{ext}"
    
    if os.path.isfile(final_path):
        return False

    if path is None and not is_stream and not is_archived and type_f:
        legacy_folders = ["Today", "Yesterday", "Last Week"]
        folders_to_check = [f for f in legacy_folders if f != folder_name]
        base_media_path = f"Profiles/{PROFILE}/Media/{type_f}"

        for old_folder in folders_to_check:
            possible_old_path = f"{base_media_path}/{old_folder}/{id_str}{ext}"
            if os.path.isfile(possible_old_path):
                try:
                    assure_dir(os.path.dirname(final_path))
                    shutil.move(possible_old_path, final_path)
                    clean_up_empty_folder(f"{base_media_path}/{old_folder}")
                    return False 
                except: pass
    
    assure_dir(os.path.dirname(final_path))
    
    success = False
    if is_drm:
        if download_drm_video(source, final_path, id_str, post_id, specific_cookies):
            new_files += 1
            success = True
    else:
        download_file(source, final_path, timestamp)
        if os.path.exists(final_path) and os.path.getsize(final_path) > 0:
            new_files += 1
            success = True
            if (media["type"] == "video" or media["type"] == "gif") and not final_path.endswith(".mp4"):
                convert_to_mp4(final_path)

    return success

def download_file(source, path, timestamp=None):
    if not API_HEADER:
        return

    assure_dir(os.path.dirname(path))
    clean_headers = {
        "User-Agent": API_HEADER.get("User-Agent", "Mozilla/5.0")
    }

    try:
        r = requests.get(source, stream=True, headers=clean_headers, cookies={})
        
        if r.status_code == 200:
            with open(path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)

            if timestamp is not None:
                set_file_mtime(path, timestamp)
        else:
            logging.error(f"Error {r.status_code} - Need clean cache: {source}")

    except Exception as e:
        logging.error(f"Crash download: {e}")

def get_id_from_path(path):
    last_index = path.rfind("/")
    second_last_index = path.rfind("/", 0, last_index - 1)
    id = path[second_last_index + 1:last_index]
    return id

def download_posts(posts, is_archived, pbar, is_stream=False, file_callback=None):
    media_downloaded = 0
    skipped_count = 0 
    config = load_config()
    
    save_text_with_media = not config['settings']['disable_download_post_with_txt']
    download_tagged_posts = config['settings']['download_tagged_posts']
    merge_tagged_media = config['settings']['merge_tagged_media']

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []
        for post in posts:
            text = post.get("text") or ""
            post_id = str(post.get("id"))

            contains_tags = any(tag in (text.lower() if text else "") for tag in ["#adv", "#ad", "#advertising", "#ad24", "#ads", "spin", "Advertisement"])

            if "text" in post and post["text"] is not None and not download_tagged_posts and contains_tags:
                skipped_count += 1
                continue

            if "media" not in post or ("canViewMedia" in post and not post["canViewMedia"]):
                continue
                
            post_timestamp_unix = float(post["postedAtPrecise"])
            post_timestamp = dt.datetime.fromtimestamp(post_timestamp_unix)
            post_date_str = post_timestamp.strftime('%Y-%m-%dT%H_%M_%S')
            
            for media in post["media"]:
                # Important fix: Set to None first to avoid crashes on normal media
                cf_cookies = None 
                
                source_url = None
                files = media.get("files", {})
                
                if "drm" in files and files["drm"]:
                    source_url = files["drm"].get("manifest", {}).get("dash")
                    
                    # Get CloudFront cookies
                    signature = files["drm"].get("signature", {}).get("dash", {})
                    if signature:
                        p = signature.get("CloudFront-Policy")
                        s = signature.get("CloudFront-Signature")
                        k = signature.get("CloudFront-Key-Pair-Id")
                        if p and s and k:
                            cf_cookies = f"CloudFront-Policy={p}; CloudFront-Signature={s}; CloudFront-Key-Pair-Id={k}"
                
                if not source_url:
                    source_url = files.get("source", {}).get("url") or files.get("full", {}).get("url")

                if source_url:
                    path = None
                    # Path setup
                    if download_tagged_posts and contains_tags:
                        base_path = f"Profiles/{PROFILE}/Media/Tag-Post"
                        path = f"/{base_path}/" if merge_tagged_media else f"/{base_path}/{media['type']}s/"
                    elif save_text_with_media:
                        post_dir = f"Profiles/{PROFILE}/Media/Posts/{post_date_str}"
                        assure_dir(post_dir)
                        if "text" in post and post.get("text"):
                            text_file_path = f"{post_dir}/_text.txt"
                            if not os.path.exists(text_file_path):
                                with open(text_file_path, "w", encoding='utf-8') as f: f.write(post["text"])
                        path = f"/Media/Posts/{post_date_str}/"
                    
                    # Pass cookies to the download function
                    futures.append(executor.submit(download_media, media, is_archived, path, post_timestamp, is_stream, source_url, post_id, cf_cookies))
        
        # Bar Fix: Always update
        for future in as_completed(futures):
            try:
                success = future.result()
                if success: media_downloaded += 1
            except:
                pass
            finally:
                if file_callback: file_callback()
                
    return media_downloaded, skipped_count

class FakeBar:
    def update(self, n=1): pass
    def set_description(self, desc): pass
    def close(self): pass
    @property
    def n(self): return 0

def clean_filename(filename):
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename
    
def download_highlights(highlights, file_callback=None):
    if not highlights["list"]:
        return

    # Load configuration
    config = load_config()
    disable_cover = config["settings"]["disable_cover_highlights"]
    disable_folder = config["settings"]["disable_folder_highlights"]

    base_path = f"Profiles/{PROFILE}/Media/Highlights/"
    assure_dir(base_path)
    
    # 1. GATHER LINKS (Sequential to keep API happy)
    download_tasks = [] # List of (url, path)
    
    for highlight in highlights["list"]:
        title = clean_filename(highlight.get("title", "Untitled"))
        highlight_id = highlight.get("id", None)
        
        if highlight_id:
            # Create folder
            save_path = base_path
            if not disable_folder:
                save_path += f"{title}/"
                assure_dir(save_path)

            # Cover Image
            cover_url = highlight.get("cover", None)
            if cover_url and not disable_cover:
                download_tasks.append((cover_url, save_path + "!cover.jpg"))

            # API Request (Sequential = Safe)
            try:
                details = get_highlight_details_API(highlight_id)
                stories = details.get("stories", [])
                
                for story in stories:
                    media_items = story.get("media", [])
                    for media_item in media_items:
                        # Extract URL
                        source_url = None
                        files = media_item.get("files", {})
                        if "source" in files: source_url = files["source"].get("url")
                        elif "full" in files: source_url = files["full"].get("url")
                        elif "thumb" in files: source_url = files["thumb"].get("url")
                        elif "preview" in files: source_url = files["preview"].get("url")
                        
                        if source_url:
                            download_tasks.append((source_url, save_path, media_item))
            except:
                pass

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []
        for item in download_tasks:
            if len(item) == 2:
                futures.append(executor.submit(download_file, item[0], item[1]))
            else:
                futures.append(executor.submit(download_media, item[2], False, path=item[1], source_url=item[0]))
        
        for future in as_completed(futures):
            try: future.result()
            except: pass
            finally:
                if file_callback: file_callback()

def download_chats(chats):
    if not isinstance(chats, list):
        return

    photos_to_download = []
    videos_to_download = []

    for chat in chats:
        if not isinstance(chat, dict):
            continue
            
        text = chat.get("text", "").lower()
        if ("#adv" in text or "#ad" in text or "spin" in text or "#spins" in text or "#Advertisement" in text or "https://of.tv/" in text):
            continue

        media_items = chat.get("media", [])
        for media_item in media_items:
            media_type = media_item["type"]

            source_url = None
            if "full" in media_item["files"]:
                source_url = media_item["files"]["full"].get("url")
            elif "thumb" in media_item["files"]:
                source_url = media_item["files"]["thumb"].get("url")
            elif "preview" in media_item["files"]:
                source_url = media_item["files"]["preview"].get("url")
            elif "squarePreview" in media_item["files"]:
                source_url = media_item["files"]["squarePreview"].get("url")

            if source_url:
                if media_type == "photo":
                    photos_to_download.append((media_item, source_url))
                elif media_type == "video":
                    videos_to_download.append((media_item, source_url))

    if not photos_to_download and not videos_to_download:
        return

    chat_path = "Profiles/" + PROFILE + "/Media/Chat"
    assure_dir(chat_path)

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []
        
        if photos_to_download:
            photos_path = chat_path + "/Photos/"
            assure_dir(photos_path)
            for media_item, source_url in photos_to_download:
                futures.append(executor.submit(download_media, media_item, False, path=photos_path, source_url=source_url))

        if videos_to_download:
            videos_path = chat_path + "/Videos/"
            assure_dir(videos_path)
            for media_item, source_url in videos_to_download:
                futures.append(executor.submit(download_media, media_item, False, path=videos_path, source_url=source_url))

        for future in as_completed(futures):
            future.result()

def download_stories(stories):
    if not stories:
        return

    assure_dir("Profiles/" + PROFILE + "/Media/Stories")
    
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []
        
        for story in stories:
            media_items = story.get("media", [])
            for media_item in media_items:
                source_url = None
                
                if "full" in media_item["files"]:
                    source_url = media_item["files"]["full"].get("url")
                elif "thumb" in media_item["files"]:
                    source_url = media_item["files"]["thumb"].get("url")
                elif "preview" in media_item["files"]:
                    source_url = media_item["files"]["preview"].get("url")
                elif "squarePreview" in media_item["files"]:
                    source_url = media_item["files"]["squarePreview"].get("url")
                
                if source_url:
                    futures.append(executor.submit(download_media, media_item, False, path="Profiles/" + PROFILE + "/Media/Stories/", source_url=source_url))
                else:
                    logging.warning(f"URL not foundd media_item with ID {media_item.get('id')}")

        for future in as_completed(futures):
            future.result()

def get_all_videos(videos):
    with ThreadPoolExecutor(max_workers=8) as executor:
        has_more_videos = True

        while has_more_videos:
            futures = [executor.submit(
                api_request,
                "/users/" + PROFILE_ID + "/posts/videos",
                getdata={"limit": "999999", "order": "publish_date_desc", "beforePublishTime": videos[-1]["postedAtPrecise"] if videos else None},
            ) for _ in range(8)]
            
            for future in as_completed(futures):
                extra_video_posts = future.result()
                
                if isinstance(extra_video_posts, list):
                    videos.extend(extra_video_posts)
                else:
                    has_more_videos = False
                    break
            
            if not videos:
                has_more_videos = False
            
            else:
                has_more_videos = any(len(future.result()) > 0 for future in futures)
    return videos

def load_photo_cache():
    cache_file_path = os.path.join(CACHE_DIR, f"cache_{PROFILE_ID}_photos.json")
    if os.path.exists(cache_file_path):
        with open(cache_file_path, 'r') as f:
            return json.load(f)
    return {}

def save_photo_cache(photo_cache):
    cache_file_path = os.path.join(CACHE_DIR, f"cache_{PROFILE_ID}_photos.json")
    with open(cache_file_path, 'w') as f:
        json.dump(photo_cache, f)


def get_all_photos(images):
    with ThreadPoolExecutor(max_workers=8) as executor:
        has_more_images = True

        while has_more_images:
            futures = [executor.submit(
                api_request,
                "/users/" + PROFILE_ID + "/posts/photos",
                getdata={"limit": "999999", "order": "publish_date_desc", "beforePublishTime": images[-1]["postedAtPrecise"] if images else None},
            ) for _ in range(8)]
            
            for future in as_completed(futures):
                extra_img_posts = future.result()
                images.extend(extra_img_posts)
            
            has_more_images = any(len(future.result()) > 0 for future in futures)
    return images

def get_all_archived(archived):
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        len_archived = len(archived)
        has_more_archived = len_archived > 0

        while has_more_archived:
            len_archived = len(archived)
            future = executor.submit(
                api_request,
                "/users/" + PROFILE_ID + "/posts/archived",
                getdata={"limit": "999999", "order": "publish_date_desc", "beforePublishTime": archived[len_archived - 1]["postedAtPrecise"]},
            )
            extra_archived_posts = future.result()
            archived.extend(extra_archived_posts)
            has_more_archived = len(extra_archived_posts) > 0

    return archived

def get_all_streams(streams):
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        len_streams = len(streams)
        has_more_streams = len_streams > 0

        while has_more_streams:
            len_streams = len(streams)
            future = executor.submit(
                api_request,
                "/users/" + PROFILE_ID + "/posts/streams",
                getdata={"limit": "999999", "order": "publish_date_desc", "beforePublishTime": streams[len_streams - 1]["postedAtPrecise"]},
            )
            extra_stream_posts = future.result()
            streams.extend(extra_stream_posts)
            has_more_streams = len(extra_stream_posts) > 0

    return streams

def fetch_all_highlights():
    highlights = []
    offset = 0
    limit = 5
    
    while True:
        response = api_request(f"/users/{PROFILE_ID}/stories/highlights", getdata={"limit": str(limit), "offset": str(offset)})
                
        if not response['list'] or len(response['list']) < 5:
            highlights.extend(response['list'])
            break
        
        highlights.extend(response['list'])
        offset += limit

    return highlights

def get_all_highlights():
    return fetch_all_highlights()

def get_all_labels():
    labels = []
    offset = 0
    limit = 10
    while True:
        params = {"limit": str(limit), "offset": str(offset), "non-empty": "1"}
        response = api_request(f"/users/{PROFILE_ID}/labels", getparams=params)
        
        if isinstance(response, dict) and 'list' in response:
            current_list = response['list']
        elif isinstance(response, list):
            current_list = response
        else:
            break
            
        if not current_list:
            break
            
        labels.extend(current_list)
        if len(current_list) < limit:
            break   
        offset += limit
    return labels

def get_posts_from_label(label_id):
    all_posts = []
    offset = 0
    while True:
        data = api_request(f"/users/{PROFILE_ID}/posts", getdata={"limit": "100", "offset": str(offset), "label": str(label_id)})
        if not data or not isinstance(data, list):
            break
        all_posts.extend(data)
        if len(data) < 100:
            break
        offset += 100
    return all_posts

def get_all_stories():
    return api_request("/users/" + PROFILE_ID + "/stories", getdata={"limit": "999999"})

def get_all_chats():
    all_chats = []
    limit = 10
    last_id = None
    
    while True:
        params = {"limit": limit, "order": "desc", "skip_users": "all"}
        if last_id:
            params["id"] = last_id

        chats_response = api_request("/chats/" + PROFILE_ID + "/messages", getparams=params)
        chats = chats_response.get("list", [])

        if not isinstance(chats, list) or not chats:
            break
            
        for chat in chats:
            text = chat.get("text", "").lower()
            # anti spam
            if any(x in text for x in ["#adv", "#ad", "spin", "of.tv/","#Advertisement"]):
                continue
            all_chats.append(chat)

        last_id = chats[-1].get("id")
        
    return all_chats

def count_files(posts):
    count = 0
    for post in posts:
        if "media" not in post or ("canViewMedia" in post and not post["canViewMedia"]):
            continue
        count += len(post["media"])
    return count

if __name__ == "__main__":
    try:
        print(f"{Fore.YELLOW}[*] Loading Auth...{Style.RESET_ALL}")
        API_HEADER = create_auth()
        
        if not API_HEADER or "user-id" not in API_HEADER:
            print(f"{Fore.RED}ERROR: Invalid Auth.json.{Style.RESET_ALL}")
            sys.exit(1)
            
        try:
            print(f"{Fore.YELLOW}[*] Loading dynamic rules...{Style.RESET_ALL}")
            dynamic_rules = requests.get('https://raw.githubusercontent.com/DATAHOARDERS/dynamic-rules/main/onlyfans.json').json()
        except:
            print("Warning: Could not download dynamic rules (offline?)")
            dynamic_rules = {}

        print(f"{Fore.GREEN}[*] Starting User Interface...{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}STARTUP ERROR: {e}{Style.RESET_ALL}")
        sys.exit(1)

    init() 
    app = OnlySnapTUI()
    app.run()