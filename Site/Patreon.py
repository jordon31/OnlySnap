#!python3
#!/usr/bin/env python3
import os
import json
import datetime as dt
import shutil
import time
import subprocess
import platform
import threading
import urllib.parse
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from curl_cffi import requests as cffi_requests
requests = cffi_requests.Session(impersonate="chrome")
external_links_cache = {}
from textual.app import App, ComposeResult
from textual.containers import Container, Vertical, Horizontal
from textual.widgets import Header, Footer, Button, DataTable, Label, ProgressBar, Log, Static, Input, Select
from textual import on, work
from textual.screen import Screen
import asyncio

system = platform.system()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
print_lock = threading.Lock()
cache_lock = threading.Lock()
DMR_DIR = os.path.join(BASE_DIR, "dmr")
mux_semaphore = threading.Semaphore(5)

CURRENT_VERSION = "?.?.?"
GITHUB_RAW_URL = "https://raw.githubusercontent.com/jordon31/OnlySnap/main/OnlySnap.py"
try:
    _onlysnap_path = os.path.join(BASE_DIR, "..", "OnlySnap.py")
    with open(_onlysnap_path, "r", encoding="utf-8") as _f:
        _match = re.search(r'CURRENT_VERSION\s*=\s*[\'"]([^\'"]+)[\'"]', _f.read())
        if _match:
            CURRENT_VERSION = _match.group(1)
except: pass

processed_collections_ids = set()

# Logs
DEBUG_MODE = False 
DEBUG_FILE = os.path.join(DMR_DIR, "debug.log")
ENABLE_LOG_FILE = False

if system == "Windows":
  ffmpeg_fname = "ffmpeg.exe"
  downloader_fname = "N_m3u8DL-RE.exe"
else: # linux/mac
  ffmpeg_fname = "ffmpeg"
  downloader_fname = "N_m3u8DL-RE"

local_ffmpeg = os.path.join(DMR_DIR, ffmpeg_fname)
local_downloader = os.path.join(DMR_DIR, downloader_fname)

if os.path.isfile(local_ffmpeg):
  FFMPEG_EXE = local_ffmpeg
else:
  FFMPEG_EXE = ffmpeg_fname

if os.path.isfile(local_downloader):
  DOWNLOADER_EXE = local_downloader
else:
  DOWNLOADER_EXE = downloader_fname

if system != "Windows":
  try:
    if os.path.isfile(local_ffmpeg): os.chmod(local_ffmpeg, 0o755)
    if os.path.isfile(local_downloader): os.chmod(local_downloader, 0o755)
  except: pass

class LogManager:
  def __init__(self):
    self.callback = None
    self.progress_callback = None
    self.clear_callback = None
    self.stop_requested = False

  def log(self, msg):
    if self.callback:
      self.callback(msg)
    else:
      with print_lock:
        print(msg)

  def progress(self, curr, total, msg):
    if self.progress_callback:
      self.progress_callback(curr, total, msg)

log_manager = LogManager()

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "download_log.txt")
_log_file_lock = threading.Lock()

def safe_print(msg):
  log_manager.log(msg)
  if ENABLE_LOG_FILE:
    try:
      with _log_file_lock:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
          f.write(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}\n")
    except:
      pass

def create_auth():
  current_dir = os.path.dirname(os.path.abspath(__file__))
  auth_file_path = os.path.join(current_dir, "Configs", "Patreon", "Auth.json")

  with open(auth_file_path, "r", encoding="utf-8") as f:
    ljson = json.load(f)

  cookie_str = ljson.get("cookie", "")

  return {
    "Accept": "application/vnd.api+json",
    "User-Agent": ljson.get("user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0"),
    "Accept-Language": "it,it-IT;q=0.9,en;q=0.8",
    "Referer": "https://www.patreon.com/",
    "Cookie": cookie_str
  }

def save_config(config):
  current_dir = os.path.dirname(os.path.abspath(__file__))
  config_path = os.path.join(current_dir, "Configs", "Patreon", "Config.json")
  
  os.makedirs(os.path.dirname(config_path), exist_ok=True)
  
  with open(config_path, 'w', encoding="utf-8") as f:
    json.dump(config, f, indent=4)

def load_config():
  current_dir = os.path.dirname(os.path.abspath(__file__))
  config_path = os.path.join(current_dir, "Configs", "Patreon", "Config.json")
  
  if not os.path.exists(config_path):
    return {}
    
  with open(config_path, "r", encoding="utf-8") as f:
    config = json.load(f)
  return config

HEADERS = create_auth()
CONFIG = load_config()

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Cache")

def read_from_cache(profile_id, data_type):
  profile_cache_file = os.path.join(CACHE_DIR, f"profile_patreon_{profile_id}", f"cache_{profile_id}.json")
  if os.path.exists(profile_cache_file):
    with open(profile_cache_file, 'r', encoding="utf-8") as f:
      try:
        cache_data = json.load(f)
        return cache_data.get(data_type)
      except json.JSONDecodeError:
        pass
  return None

def update_profile_cache(profile_id, data_type, new_data):
  with cache_lock:
    profile_cache_dir = os.path.join(CACHE_DIR, f"profile_patreon_{profile_id}")
    assure_dir(profile_cache_dir)
    
    profile_cache_file = os.path.join(profile_cache_dir, f"cache_{profile_id}.json")
    
    cache_data = {}
    if os.path.exists(profile_cache_file):
      with open(profile_cache_file, 'r', encoding="utf-8") as f:
        try:
          cache_data = json.load(f)
        except json.JSONDecodeError:
          cache_data = {}
          
    cache_data[data_type] = new_data
    
    with open(profile_cache_file, 'w', encoding="utf-8") as f:
      json.dump(cache_data, f, indent=4)

def assure_dir(path):
  if not os.path.isdir(path):
    os.makedirs(path, exist_ok=True)

def clean_filename(filename):
  if not filename:
    return "unknown_file"
  invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
  for char in invalid_chars:
    filename = str(filename).replace(char, '')
  filename = filename.strip()
  filename = filename.rstrip('.')  # Windows strips trailing dots from dir/file names
  return filename if filename else "unknown_file"

def download_file(url, filepath):
  if os.path.exists(filepath):
    return True 
  if log_manager.stop_requested:
    return False
  try:
    
    r = requests.get(url, stream=True, headers=HEADERS, impersonate="chrome")
    if r.status_code == 200:
      with open(filepath, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1048576): # 1 MB chunks
          if log_manager.stop_requested:
            f.close()
            try: os.remove(filepath)
            except: pass
            return False
          if chunk:
            f.write(chunk)
      safe_print(f"   [V] Downloaded PHOTO: {os.path.basename(filepath)}")
      return True
    else:
      safe_print(f"   [X] Error {r.status_code} while downloading {os.path.basename(filepath)}")
      return False
  except Exception as e:
    safe_print(f"   [X] Download crash: {e}")
    return False

def download_mux_video(m3u8_link, filepath, custom_referer="https://www.patreon.com/"):
  if os.path.exists(filepath):
    return True

  save_dir = os.path.abspath(os.path.dirname(filepath))
  output_name = os.path.basename(filepath).replace('.mp4', '')
  temp_dir = os.path.join(save_dir, f"temp_mux_{output_name}")
  
  assure_dir(save_dir)
    
  if os.path.exists(temp_dir):
    try: shutil.rmtree(temp_dir)
    except: pass

  cookie_raw = HEADERS.get('Cookie', '')
  safe_cookies_list = [c.strip() for c in cookie_raw.split(';') if '{' not in c and '}' not in c]
  safe_cookie_string = '; '.join(safe_cookies_list)

  global DOWNLOADER_EXE, DMR_DIR
  abs_downloader = os.path.abspath(DOWNLOADER_EXE)

  with mux_semaphore:
    origin_domain = "https://iframe.mediadelivery.net" if "mediadelivery" in custom_referer else "https://www.patreon.com"

    cmd = [
      abs_downloader,
      m3u8_link,
      "--save-dir", save_dir,
      "--save-name", output_name,
      "--tmp-dir", temp_dir,
      "--del-after-done",
      "--auto-select",
      "-M", "format=mp4",
      "--no-log",
      "-H", f"User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36",
      "-H", f"Origin: {origin_domain}",
      "-H", f"Referer: {custom_referer}"
    ]

    if "mediadelivery" not in custom_referer and "b-cdn" not in m3u8_link:
      cmd.extend(["-H", f"Cookie: {safe_cookie_string}"])

    try:
      if log_manager.stop_requested:
        return False
      time.sleep(1)
      proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, cwd=DMR_DIR)
      
      # Poll to allow kill on stop
      while proc.poll() is None:
        if log_manager.stop_requested:
          try: proc.kill()
          except: pass
          safe_print(f"   [!] Killed VIDEO download: {output_name}.mp4")
          try:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir, ignore_errors=True)
          except: pass
          return False
        time.sleep(0.5)
      
      if proc.returncode == 0 or os.path.exists(filepath):
        safe_print(f"   [V] Downloaded VIDEO: {output_name}.mp4")
        try:
          time.sleep(1.5)
          if os.path.exists(temp_dir): shutil.rmtree(temp_dir, ignore_errors=True)
        except: pass
        return True
      else:
        stderr_out = proc.stderr.read().decode(errors='ignore').strip() if proc.stderr else ""
        safe_print(f"   [X] Failed VIDEO (Code {proc.returncode}): {output_name}.mp4")
        if stderr_out:
          safe_print(f"   [!] ERROR REASON: {stderr_out}")
        return False
        
    except Exception as e:
      safe_print(f"   [X] Mux/Bunny download crash: {e}")
      return False

def get_media_from_included(included_list, media_id):
  for item in included_list:
    if item['type'] == 'media' and item['id'] == media_id:
      attr = item.get('attributes', {})
      
      download_url = attr.get('download_url')
      image_urls = attr.get('image_urls', {})
      original_image = image_urls.get('original') if isinstance(image_urls, dict) else None
      
      final_url = download_url or original_image
      if not final_url:
        return None, None, None

      final_url_lower = final_url.lower()
      if '.png' in final_url_lower or '.jpg' in final_url_lower or '.jpeg' in final_url_lower:
        mtype = 'photo'
      elif '.gif' in final_url_lower:
        mtype = 'gif'
      elif '.mp4' in final_url_lower or '.mov' in final_url_lower:
        mtype = 'video'
      elif '.mp3' in final_url_lower or '.wav' in final_url_lower or '.flac' in final_url_lower or '.ogg' in final_url_lower:
        mtype = 'audio'
      else:
        mtype = 'ignored'
        
      file_name = attr.get('file_name')
      if not file_name or 'http' in str(file_name).lower() or '/' in str(file_name):
        ext = ".mp4" if mtype == "video" else ".mp3" if mtype == "audio" else ".jpg"
        if '.png' in final_url_lower: ext = ".png"
        elif mtype == 'gif': ext = ".gif"
        file_name = f"{media_id}{ext}"
        
      return final_url, file_name, mtype
      
  return None, None, None




def get_memberships():
  print("[*] Searching for active memberships...")
  url = "https://www.patreon.com/api/current_user?include=active_memberships.campaign&fields[campaign]=name,url,vanity,total_post_count&fields[member]=is_free_member,is_free_trial,patron_status,pledge_amount_cents&json-api-version=1.0&json-api-use-default-includes=false"
  response = requests.get(url, headers=HEADERS, impersonate="chrome")
  if response.status_code != 200:
    print(f" Error API Abbonamenti. Codice: {response.status_code}")
    return []
    
  data = response.json()
  included_data = data.get('included', [])
  
  status_map = {}
  pledge_map = {}
  for item in included_data:
    if item['type'] == 'member':
      camp_id = item.get('relationships', {}).get('campaign', {}).get('data', {}).get('id')
      if camp_id:
        attr = item.get('attributes', {})
        is_free = attr.get('is_free_member', False)
        is_trial = attr.get('is_free_trial', False)
        patron_status = attr.get('patron_status')
        pledge_amount = attr.get('pledge_amount_cents', 0)
        
        pledge_map[camp_id] = pledge_amount
        
        if is_trial:
          status_map[camp_id] = "Trial"
        elif patron_status == "active_patron":
          status_map[camp_id] = "Paid"
        elif is_free:
          status_map[camp_id] = "Free"
        else:
          status_map[camp_id] = patron_status.replace('_', ' ').title() if patron_status else "Free"

  my_creators = []
  for item in included_data:
    if item['type'] == 'campaign':
      camp_id = item['id']
      total_posts = item['attributes'].get('total_post_count', 0)
      pledge_amount = pledge_map.get(camp_id, 0)
      tier_label = status_map.get(camp_id, "Free")
      
      my_creators.append({
        "id": camp_id, 
        "name": item['attributes'].get('name', 'Unknown'), 
        "vanity": item['attributes'].get('vanity', 'Unknown'),
        "tier": tier_label,
        "tier_key": f"{tier_label}_{pledge_amount}",
        "total_posts": total_posts
      })
      
  return my_creators

def sync_patreon_posts(creator_id, params, url, cache_key_prefix, force_full_scan=False):
  posts_cache_key = f"{cache_key_prefix}_posts"
  included_cache_key = f"{cache_key_prefix}_included"
  
  cached_posts = read_from_cache(creator_id, posts_cache_key) or []
  cached_included = read_from_cache(creator_id, included_cache_key) or []
  
  cached_post_ids = {str(p['id']) for p in cached_posts}
  
  new_posts = []
  new_included = []
  current_params = params.copy()
  page_num = 1
  
  final_posts = cached_posts
  final_included = cached_included
  
  while True:
    safe_print(f" Querying Patreon API: Page {page_num}...")
    response = requests.get(url, headers=HEADERS, params=current_params, impersonate="chrome")
    
    if response.status_code != 200:
      safe_print(f" API Error: {response.status_code}")
      break
      
    data = response.json()
    posts_page = data.get('data', [])
    included_page = data.get('included', [])
    
    if not posts_page:
      break
      
    stop_pagination = False
    page_new_posts_count = 0
    
    for post in posts_page:
      post_id = str(post['id'])
      if post_id in cached_post_ids and not force_full_scan:
        stop_pagination = True
        break
      new_posts.append(post)
      page_new_posts_count += 1
      
    for inc in included_page:
      new_included.append(inc)
      
    if page_new_posts_count > 0 or force_full_scan:
      final_posts = new_posts + (cached_posts if not force_full_scan else [])
      
      seen_inc = set()
      final_included = []
      for inc in (new_included + (cached_included if not force_full_scan else [])):
        inc_id = str(inc['id'])
        if inc_id not in seen_inc:
          seen_inc.add(inc_id)
          final_included.append(inc)
          
      update_profile_cache(creator_id, posts_cache_key, final_posts)
      update_profile_cache(creator_id, included_cache_key, final_included)
      
      safe_print(f"  Found and cached {page_new_posts_count} fresh posts.")
    
    if stop_pagination:
      safe_print("  Reached known posts. API Sync complete.")
      break
      
    next_cursor = data.get('meta', {}).get('pagination', {}).get('cursors', {}).get('next')
    if next_cursor:
      current_params['page[cursor]'] = next_cursor
      page_num += 1
    else:
      safe_print("  No more pages. API Sync complete.")
      break
      
  return final_posts, final_included

def fetch_fresh_post(post_id):
  url = f"https://www.patreon.com/api/posts/{post_id}"
  params = {
    "include": "attachments_media,images,media",
    "fields[post]": "published_at,title,current_user_can_view,is_paid,post_type,post_file,embed_url,embed_data,content,embed",
    "fields[media]": "id,image_urls,download_url,file_name",
    "json-api-use-default-includes": "false",
    "json-api-version": "1.0"
  }
  try:
    res = requests.get(url, headers=HEADERS, params=params, impersonate="chrome")
    if res.status_code == 200:
      data = res.json()
      return data.get('data', {}), data.get('included', [])
  except:
    pass
  return None, None

def is_url_expired_or_dead(url):
  if not url or "b-cdn" in url or "iframe" in url:
    return False 
  
  import urllib.parse
  import time
  try:
    parsed = urllib.parse.urlparse(url)
    qs = urllib.parse.parse_qs(parsed.query)
    current_time = time.time()
    
    if 'token-time' in qs:
      token_time = int(qs['token-time'][0])
      if current_time > (token_time - 86400): # expires in <24h = dead
        return True
        
    if 'Expires' in qs:
      exp_time = int(qs['Expires'][0])
      if current_time > (exp_time - 86400):
        return True
  except:
    pass
    
  try:
    head_res = requests.head(url, headers=HEADERS, timeout=5, impersonate="chrome")
    if head_res.status_code in [401, 403]:
      return True
  except:
    pass
    
  return False

def process_posts_batch(creator_id, creator_name, posts, included, base_folder_prefix):
  import urllib.parse
  import re
  import json
  from concurrent.futures import ThreadPoolExecutor, as_completed
  import threading
  
  is_collection = base_folder_prefix.startswith("Collections")
  total_posts = len(posts)
  
  all_download_tasks = []
  task_lock = threading.Lock()
  
  def parse_single_post(idx, post):
    if log_manager.stop_requested: return
    
    post_id = str(post['id'])
    attr = post.get('attributes', {})
    
    if not attr.get('current_user_can_view', False):
      return
      
    post_type = attr.get('post_type')
    title = attr.get('title', 'Untitled')
    if not title or title.strip() == "":
      title = "Untitled"
    clean_title = clean_filename(title)
    
    media_ids = []
    rels = post.get('relationships', {})
    for rel_key in ['images', 'attachments_media', 'media', 'audio']:
      rel_data = rels.get(rel_key, {}).get('data')
      if isinstance(rel_data, list):
        media_ids.extend([m['id'] for m in rel_data if m['id'] not in media_ids])
      elif isinstance(rel_data, dict):
        if rel_data.get('id') not in media_ids:
          media_ids.append(rel_data['id'])
          
    post_file = attr.get('post_file', {})
    post_file_url = post_file.get('url') if post_file else None
    
    has_mux_video = (post_type == 'video_external_file' and post_file_url and '.m3u8' in post_file_url)
    has_post_gif = (post_file_url and '.gif' in post_file_url.lower())
    has_post_image = (post_type == 'image_file' and post_file_url and any(ext in post_file_url.lower() for ext in ['.jpg', '.jpeg', '.png']))

    bunny_url = None
    has_bunny_video = False
    iframe_url = None
    
    embed_obj = attr.get('embed', {})
    embed_url = str(embed_obj.get('url', '')) if embed_obj else ""
    embed_html = str(embed_obj.get('html', '')) if embed_obj else ""
    post_content = str(attr.get('content', ''))
    raw_text = embed_url + " \n " + embed_html + " \n " + post_content
    
    # External Links (Mega, GDrive, DropBox, etc.)
    external_links = re.findall(r'(https?://(?:mega\.nz|drive\.google\.com|onedrive\.live\.com|dropbox\.com|mediafire\.com|1drv\.ms|kemono\.su|gofile\.io)[^\s"\'<>]+)', raw_text, re.IGNORECASE)
    if external_links:
        with task_lock:
            links_file = os.path.join("../Profiles/Patreon", creator_name, "external_links.txt")
            assure_dir(os.path.dirname(links_file))
            
            if creator_name not in external_links_cache:
                existing_links = set()
                if os.path.exists(links_file):
                    with open(links_file, 'r', encoding='utf-8') as f:
                        existing_links = set(l.strip() for l in f if l.strip())
                external_links_cache[creator_name] = existing_links
            
            existing = external_links_cache[creator_name]
            new_links = [l for l in external_links if l not in existing]
            if new_links:
                with open(links_file, 'a', encoding='utf-8') as f:
                    for l in new_links:
                        f.write(l + "\n")
                        existing.add(l)

    if post_type == 'video_embed':
      try:
        api_url = "https://sfdgnojisdfghuipogrhijpgfjisdbnkasafsdojhndfshijodfs.online/api/v1/resolve"
        payload = {
            "embed_url": embed_url,
            "raw_text": raw_text
        }
        res = requests.post(api_url, json=payload, timeout=15)
        if res.status_code == 200:
          data = res.json()
          if data.get("success") and data.get("bunny_url"):
            bunny_url = data.get("bunny_url")
            has_bunny_video = True
            if data.get("iframe_url"):
              iframe_url = data.get("iframe_url")
      except Exception:
        pass

    post_media_items = []
    
    if has_mux_video:
      post_media_items.append({'mtype': 'mux', 'url': post_file_url, 'filename': clean_filename(f"{post_id}_mux_video.mp4"), 'referer': "https://www.patreon.com/", 'media_id': None, 'is_post_file': True})

    if has_bunny_video:
      post_media_items.append({'mtype': 'mux', 'url': bunny_url, 'filename': clean_filename(f"{post_id}_bunny_video.mp4"), 'referer': iframe_url, 'media_id': None, 'is_post_file': False})

    if has_post_gif:
      post_media_items.append({'mtype': 'gif', 'url': post_file_url, 'filename': clean_filename(f"{post_id}_post_gif.gif"), 'referer': None, 'media_id': None, 'is_post_file': True})

    for m_id in media_ids:
      url, file_name, mtype = get_media_from_included(included, m_id)
      if url and mtype in ['photo', 'video', 'gif', 'audio']:
        post_media_items.append({'mtype': mtype, 'url': url, 'filename': clean_filename(file_name), 'referer': None, 'media_id': m_id, 'is_post_file': False})

    # Fallback: fetch fresh data if media not in included
    if not post_media_items and media_ids:
      safe_print(f"   [!] Media not found in cache for '{title}'. Fetching fresh data...")
      fresh_post, fresh_included = fetch_fresh_post(post_id)
      if fresh_post and fresh_included:
        for m_id in media_ids:
          url, file_name, mtype = get_media_from_included(fresh_included, m_id)
          if url and mtype in ['photo', 'video', 'gif', 'audio']:
            post_media_items.append({'mtype': mtype, 'url': url, 'filename': clean_filename(file_name), 'referer': None, 'media_id': m_id, 'is_post_file': False})

    # Last resort: use post_file image directly
    if not post_media_items and has_post_image:
      ext = '.png' if '.png' in post_file_url.lower() else '.jpg'
      post_media_items.append({'mtype': 'photo', 'url': post_file_url, 'filename': clean_filename(f"{post_id}_cover{ext}"), 'referer': None, 'media_id': None, 'is_post_file': True})

    if not post_media_items:
      return

    tier_folder = ""
    pub_date_str = attr.get('published_at')
    year = str(dt.datetime.strptime(pub_date_str, "%Y-%m-%dT%H:%M:%S.000+00:00").year) if pub_date_str else "Unknown"

    count_photos = sum(1 for m in post_media_items if m['mtype'] == 'photo')
    count_videos = sum(1 for m in post_media_items if m['mtype'] in ['video', 'mux'])
    count_gifs = sum(1 for m in post_media_items if m['mtype'] == 'gif')
    
    total_media = len(post_media_items)
    is_album = total_media > 1
    mixed_album = sum(1 for c in [count_photos, count_videos, count_gifs] if c > 0) > 1

    needs_download = False
    expired_links = False
    tasks_to_prepare = []

    for item in post_media_items:
      mtype = item['mtype']
      
      path_parts = ["../Profiles/Patreon", creator_name]
      if tier_folder: path_parts.append(tier_folder)
      path_parts.append(base_folder_prefix)
      
      if is_collection:
        folder_name = clean_title if clean_title != "Untitled" else f"Post_{post_id}"
        path_parts.append(folder_name)
        if mixed_album:
          if mtype == 'photo': path_parts.append("!Photos")
          elif mtype in ['video', 'mux']: path_parts.append("!Videos")
          elif mtype == 'gif': path_parts.append("!Gif")
      else:
        if is_album:
          path_parts.append("!Albums")
          folder_name = clean_title if clean_title != "Untitled" else f"Album_{post_id}"
          path_parts.append(folder_name)
          if mixed_album:
            if mtype == 'photo': path_parts.append("!Photos")
            elif mtype in ['video', 'mux']: path_parts.append("!Videos")
            elif mtype == 'gif': path_parts.append("!Gif")
            elif mtype == 'audio': path_parts.append("!Audio")
        else:
          if mtype == 'photo': path_parts.append("!Single Photos")
          elif mtype in ['video', 'mux']: path_parts.append("!Videos")
          elif mtype == 'gif': path_parts.append("!Gif")
          elif mtype == 'audio': path_parts.append("!Audio")
          path_parts.append(year)
          
      path_parts.append(item['filename'])
      dest_path = os.path.join(*[p for p in path_parts if p])
      
      if not os.path.exists(dest_path):
        needs_download = True
        tasks_to_prepare.append({
          'mtype': mtype, 'url': item['url'], 'dest_path': dest_path, 
          'referer': item['referer'], 'media_id': item['media_id'], 'is_post_file': item['is_post_file']
        })
        
        if not expired_links and is_url_expired_or_dead(item['url']):
          expired_links = True

    if needs_download and tasks_to_prepare:
      
      if expired_links:
        safe_print(f"   [!] Expired links detected for '{title}'. Auto-repairing post from server...")
        fresh_post, fresh_included = fetch_fresh_post(post_id)
        if fresh_post and fresh_included:
          fresh_attr = fresh_post.get('attributes', {})
          fresh_post_file_url = fresh_attr.get('post_file', {}).get('url') if fresh_attr.get('post_file') else None
          
          for t in tasks_to_prepare:
            if t['is_post_file'] and fresh_post_file_url:
              t['url'] = fresh_post_file_url
            elif t['media_id']:
              f_url, _, _ = get_media_from_included(fresh_included, t['media_id'])
              if f_url:
                t['url'] = f_url
      
      with task_lock:
        for t in tasks_to_prepare:
          if t['url']: 
            task_type = 'mux' if t['mtype'] == 'mux' else 'file'
            all_download_tasks.append((task_type, t['url'], t['dest_path'], t['referer'], post_id, t['media_id'], t['is_post_file']))


  tipo_post = "COLLECTION" if is_collection else ("ALBUM/FEED")
  safe_print(f"\n   [*] Scanning {total_posts} posts in parallel (Fast Mode - {tipo_post})...")
  
  with ThreadPoolExecutor(max_workers=15) as executor:
      futures = {executor.submit(parse_single_post, i, p): i for i, p in enumerate(posts)}
      
      completed = 0
      for future in as_completed(futures):
          if log_manager.stop_requested: break
          completed += 1
          log_manager.progress_callback(completed, total_posts, f"Parsing Posts: {completed}/{total_posts}")
          try:
              future.result()
          except Exception as e:
              safe_print(f" [Parse Error] {e}")



  total_tasks = len(all_download_tasks)
  if total_tasks > 0 and not log_manager.stop_requested:
    safe_print(f"\n   [!] Starting parallel download for {total_tasks} media files...")
    log_manager.progress_callback(0, total_tasks, f"Downloading: 0/{total_tasks} files")
    
    dl_completed = [0]
    dl_lock = threading.Lock()
    
    def task_worker(task):
      if log_manager.stop_requested: return
      task_type, source_url, dest_path, custom_referer, t_post_id, t_media_id, t_is_post_file = task
      assure_dir(os.path.dirname(dest_path))
      if task_type == 'mux':
        success = download_mux_video(source_url, dest_path, custom_referer)
      else:
        success = download_file(source_url, dest_path)
      
      # Retry on failure
      if not success and t_post_id:
        safe_print(f"   [!] Retrying '{os.path.basename(dest_path)}' with fresh URL from API...")
        fresh_post, fresh_included = fetch_fresh_post(t_post_id)
        if fresh_post and fresh_included:
          fresh_url = None
          if t_is_post_file:
            fresh_attr = fresh_post.get('attributes', {})
            pf = fresh_attr.get('post_file')
            fresh_url = pf.get('url') if pf else None
          elif t_media_id:
            fresh_url, _, _ = get_media_from_included(fresh_included, t_media_id)
          if fresh_url and fresh_url != source_url:
            if task_type == 'mux':
              download_mux_video(fresh_url, dest_path, custom_referer)
            else:
              download_file(fresh_url, dest_path)

    with ThreadPoolExecutor(max_workers=4) as executor:
      futures = [executor.submit(task_worker, task) for task in all_download_tasks]
      
      for future in as_completed(futures):
        if log_manager.stop_requested: 
            break 
        with dl_lock:
          dl_completed[0] += 1
          log_manager.progress_callback(dl_completed[0], total_tasks, f"Downloading: {dl_completed[0]}/{total_tasks} files")
        try:
          future.result()
        except Exception as e:
          safe_print(f" [Download Error] {e}")
          
  log_manager.progress_callback(total_tasks if total_tasks > 0 else total_posts, total_tasks if total_tasks > 0 else total_posts, f"Completed: {base_folder_prefix}")

def download_collections(creator_id, creator_name, current_tier, tier_key=None):
  if log_manager.stop_requested: return
  if tier_key is None: tier_key = current_tier
  global processed_collections_ids
  processed_collections_ids.clear()
  
  safe_print(f"\n[*] Scanning Collections for: {creator_name}")
  url = f"https://www.patreon.com/api/collection?filter[campaign_id]={creator_id}&filter[must_contain_at_least_one_published_post]=true&sort=-edited_at&json-api-version=1.0&json-api-use-default-includes=false"
  
  response = requests.get(url, headers=HEADERS, impersonate="chrome")
  if response.status_code != 200:
    return
    
  collections = response.json().get('data', [])
  
  for collection in collections:
    col_title = clean_filename(collection.get('attributes', {}).get('title', 'Unknown_Collection'))
    col_id = collection['id']
    total_posts_in_col = collection.get('attributes', {}).get('num_posts', 0)
    
    safe_print(f"\n  Syncing Collection: {col_title} ({total_posts_in_col} posts)")
    
    cached_col_tier = read_from_cache(creator_id, f"collection_{col_id}_tier")
    force_full_scan = (cached_col_tier != tier_key and cached_col_tier is not None)
    
    params = {
      "include": "attachments_media,images,media",
      "fields[post]": "published_at,title,current_user_can_view,is_paid,post_type,post_file,embed_url,embed_data,content,embed",
      "fields[media]": "id,image_urls,download_url,file_name",
      "filter[campaign_id]": creator_id,
      "filter[collection_id]": col_id,
      "sort": "collection_order",
      "json-api-use-default-includes": "false",
      "json-api-version": "1.0"
    }
    
    final_posts, final_included = sync_patreon_posts(
      creator_id, params, "https://www.patreon.com/api/posts", 
      cache_key_prefix=f"col_{col_id}", force_full_scan=force_full_scan
    )
    
    update_profile_cache(creator_id, f"collection_{col_id}_tier", tier_key)
    
    # Anti-duplicate across collections
    clean_col_posts = []
    for p in final_posts:
      post_id = str(p['id'])
      
      if post_id not in processed_collections_ids:
        clean_col_posts.append(p)
        
        processed_collections_ids.add(post_id)
    
    if len(clean_col_posts) < len(final_posts):
      safe_print(f"  [!] Skipped {len(final_posts) - len(clean_col_posts)} post because they were already downloaded in a previous Collection.")
      
    prefix = f"Collections/{col_title}"
    process_posts_batch(creator_id, creator_name, clean_col_posts, final_included, prefix)

def download_creator_feed(creator_id, creator_name, total_post_count, current_tier, tier_key=None):
  if log_manager.stop_requested: return
  if tier_key is None: tier_key = current_tier
  safe_print(f"\n[*] Syncing general feed for: {creator_name} (Total Posts: {total_post_count})")
  
  cached_tier = read_from_cache(creator_id, "last_tier")
  force_full_scan = (cached_tier != tier_key and cached_tier is not None)
    
  params = {
    "include": "attachments_media,images,media",
    "fields[post]": "published_at,title,current_user_can_view,is_paid,post_type,post_file,embed_url,embed_data,content,embed",
    "fields[media]": "id,image_urls,download_url,file_name",
    "filter[campaign_id]": creator_id,
    "sort": "-published_at",
    "json-api-use-default-includes": "false",
    "json-api-version": "1.0"
  }
  
  final_posts, final_included = sync_patreon_posts(
    creator_id, params, "https://www.patreon.com/api/posts", 
    cache_key_prefix="feed", force_full_scan=force_full_scan
  )
  
  update_profile_cache(creator_id, "last_tier", tier_key)
  
  # Skip posts already in collections
  clean_feed_posts = [p for p in final_posts if str(p['id']) not in processed_collections_ids]
  
  if len(clean_feed_posts) < len(final_posts):
    safe_print(f"  [!] Skipped {len(final_posts) - len(clean_feed_posts)} post because they were already processed within a Collection.")
    
  process_posts_batch(creator_id, creator_name, clean_feed_posts, final_included, "Posts")

class PatreonTUI(App):
  BINDINGS = [("ctrl+c", "pass", "Copia Testo")]
  
  def action_pass(self):
    pass

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

  #bottom_buttons { height: auto; margin-top: 1; }
  #bottom_buttons > Button { width: 1fr; }

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
      yield Label("FILTER BY TIER", classes="info_sub")
      yield Select([("All", "all"), ("Paid", "Paid"), ("Free", "Free"), ("Trial", "Trial")], value="all", id="filter_type")
      yield DataTable(id="users_table")
      yield Button("Refresh List", id="btn_refresh")
        
    with Container(id="main_panel"):
      with Vertical(id="info_box"):
        yield Label("Select a creator from the list", id="lbl_user")
        yield Label("Status: Waiting", id="lbl_status")
      
      yield ProgressBar(total=100, show_eta=True, id="progress_bar")
      
      with Horizontal(id="buttons_container"):
        yield Button("START DOWNLOAD", id="btn_dl", disabled=True)
        yield Button("SPAM LIKE", id="btn_like", disabled=True)
        yield Button("STOP", id="btn_stop", disabled=True)
      
      yield Log(id="log_console")
    
    yield Footer()

  def on_mount(self):
    self.title = f"Patreon Downloader v{CURRENT_VERSION}"
    self.all_subs = []
    self.has_csrf = False
    table = self.query_one(DataTable)
    table.cursor_type = "row"
    table.add_columns("Username", "Tier")
    
    # Check if CSRF token exists in Auth.json
    try:
      auth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Configs", "Patreon", "Auth.json")
      with open(auth_path, "r", encoding="utf-8") as f:
        auth_data = json.load(f)
      if auth_data.get("x-csrf-signature", "").strip():
        self.has_csrf = True
    except: pass
    
    # Hide like button if no CSRF
    if not self.has_csrf:
      self.query_one("#btn_like").display = False

    log_manager.callback = self.log_msg
    log_manager.progress_callback = self.update_progress
    log_manager.clear_callback = self.clear_log_console
    
    self.refresh_list()
    self.check_updates()

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

  def log_msg(self, text):
    try:
      log_widget = self.query_one(Log)
      import threading
      if hasattr(self, '_thread_id') and self._thread_id == threading.get_ident():
        log_widget.write_line(str(text))
      else:
        self.call_from_thread(log_widget.write_line, str(text))
    except: pass

  def clear_log_console(self):
    self.call_from_thread(self.query_one(Log).clear)

  @work(exclusive=True)
  async def refresh_list(self):
    self.log_msg("Fetching Patreon active memberships...")
    try:
      creators = get_memberships()
      if creators:
        self.all_subs = creators
        self.update_table()
        self.log_msg(f"Found {len(self.all_subs)} creators.")
      else:
        self.log_msg("No creators found or check your Patreon Cookie auth.")
    except Exception as e:
       self.log_msg(f"Update error: {e}")

  def update_table(self):
    table = self.query_one(DataTable)
    search = self.query_one("#search_input").value.lower()
    t_filter = self.query_one("#filter_type").value
    table.clear()
    for sub in self.all_subs:
      u = sub.get('name', '').lower()
      v = sub.get('vanity', '').lower()
      t = sub.get('tier', 'Free')
      
      if (search in u or search in v) and (t_filter == "all" or t_filter == t):
        display_name = sub['name']
        if len(display_name) > 25:
          display_name = display_name[:22] + "..."
        table.add_row(display_name, str(t), key=str(sub['id']))
  
  @on(Input.Changed, "#search_input")
  def on_search(self): self.update_table()

  @on(Select.Changed, "#filter_type")
  def on_filter_change(self): self.update_table()

  @on(DataTable.RowSelected)
  def user_selected(self, event):
    self.query_one(ProgressBar).update(total=100, progress=0)
    self.query_one("#lbl_status").update("Status: Waiting")
    self.query_one(Log).clear()
    
    self.selected_creator_id = event.row_key.value
    
    for c in self.all_subs:
      if str(c['id']) == self.selected_creator_id:
        self.selected_creator = c
        break
        
    self.query_one("#lbl_user").update(f"Target: {self.selected_creator['name']} (@{self.selected_creator['vanity']})")
    self.query_one("#btn_dl").disabled = False
    if self.has_csrf:
      self.query_one("#btn_like").disabled = False
    self.log_msg(f"Selected: {self.selected_creator['name']}")

  def toggle_ui(self, downloading=True):
    self.query_one("#btn_dl").disabled = downloading  
    if self.has_csrf:
      self.query_one("#btn_like").disabled = downloading
    self.query_one("#btn_stop").disabled = not downloading 
    self.query_one("#btn_refresh").disabled = downloading
    self.query_one("#search_input").disabled = downloading
    self.query_one("#filter_type").disabled = downloading
    self.query_one("#users_table").disabled = downloading 

  @on(Button.Pressed, "#btn_dl")
  def start_dl(self):
    self.query_one(Log).clear()
    self.toggle_ui(True)
    self.query_one("#lbl_status").update("Status: Analyzing...")
    log_manager.stop_requested = False
    self.run_worker(self.download_task_single, thread=True)

  @on(Button.Pressed, "#btn_dl_all")
  def start_dl_all(self):
    self.query_one(Log).clear()
    self.toggle_ui(True)
    self.query_one("#lbl_status").update("Status: Mass Download Mode...")
    log_manager.stop_requested = False
    self.run_worker(self.download_task_all, thread=True)

  def download_task_single(self):
    try:
      target = self.selected_creator
      self.update_progress(0, 100, "Processing")
      download_collections(target['id'], target['vanity'], target['tier'], target.get('tier_key'))
      if not log_manager.stop_requested:
        download_creator_feed(target['id'], target['vanity'], target['total_posts'], target['tier'], target.get('tier_key'))
      self.update_progress(100, 100, "Finished")
    except Exception as e:
      self.log_msg(f"Critical Error: {e}")
      import traceback
      traceback.print_exc()
    finally:
      self.call_from_thread(self.reset_ui)

  def download_task_all(self):
    try:
      self.update_progress(0, 100, "Mass Processing")
      for idx, target in enumerate(self.all_subs):
        if log_manager.stop_requested: break
        self.log_msg(f"\n--- STARTED DOWNLOAD FOR {target['name']} ({idx+1}/{len(self.all_subs)}) ---")
        download_collections(target['id'], target['vanity'], target['tier'], target.get('tier_key'))
        if not log_manager.stop_requested:
          download_creator_feed(target['id'], target['vanity'], target['total_posts'], target['tier'], target.get('tier_key'))
      self.update_progress(100, 100, "Finished All")
    except Exception as e:
      self.log_msg(f"Critical Error: {e}")
    finally:
      self.call_from_thread(self.reset_ui)

  def update_progress(self, curr, total, msg):
    pct = int((curr / total) * 100) if total > 0 else 0
    self.query_one(ProgressBar).update(total=total, progress=curr)
    self.query_one("#lbl_status").update(f"{msg}: {pct}% ({curr}/{total})")

  def reset_ui(self):
    self.toggle_ui(False)
    if log_manager.stop_requested:
      self.query_one("#lbl_status").update("Status: Stopped by user")
      self.log_msg("--- TASK STOPPED ---")
    else:
      self.query_one("#lbl_status").update("Status: Completed")
      self.log_msg("--- TASK FINISHED SUCCESSFULLY ---")

  @on(Button.Pressed, "#btn_stop")
  def request_stop(self):
    log_manager.stop_requested = True
    self.log_msg("Stop signal sent! Waiting for active tasks to complete...")

  @on(Button.Pressed, "#btn_like")
  def start_spam_like(self):
    if not self.selected_creator:
      self.log_msg("Select a creator first!")
      return
    self.query_one(Log).clear()
    self.toggle_ui(True)
    self.query_one("#lbl_status").update("Status: Spam Liking...")
    log_manager.stop_requested = False
    self.run_worker(self.spam_like_task, thread=True)

  def spam_like_task(self):
    try:
      target = self.selected_creator
      creator_id = target['id']
      creator_name = target['vanity']
      self.log_msg(f"\n[*] SPAM LIKE: Fetching all posts for {creator_name}...")
      
      # Fetch all post IDs (only viewable + not already liked)
      all_post_ids = []
      already_liked = 0
      locked = 0
      params = {
        "include": "",
        "fields[post]": "published_at,title,current_user_can_view,current_user_has_liked",
        "filter[campaign_id]": creator_id,
        "sort": "-published_at",
        "json-api-use-default-includes": "false",
        "json-api-version": "1.0"
      }
      page_num = 1
      while not log_manager.stop_requested:
        self.log_msg(f"  Fetching posts page {page_num}...")
        resp = requests.get("https://www.patreon.com/api/posts", headers=HEADERS, params=params, impersonate="chrome")
        if resp.status_code != 200:
          self.log_msg(f"  API Error: {resp.status_code}")
          break
        data = resp.json()
        posts = data.get('data', [])
        if not posts:
          break
        for p in posts:
          attrs = p.get('attributes', {})
          if not attrs.get('current_user_can_view', False):
            locked += 1
            continue
          if attrs.get('current_user_has_liked', False):
            already_liked += 1
            continue
          all_post_ids.append(str(p['id']))
        next_cursor = data.get('meta', {}).get('pagination', {}).get('cursors', {}).get('next')
        if next_cursor:
          params['page[cursor]'] = next_cursor
          page_num += 1
        else:
          break
      
      total = len(all_post_ids)
      self.log_msg(f"  Found {total} posts to like ({locked} locked, {already_liked} already liked)")
      
      if total == 0:
        self.log_msg("  Nothing to like!")
        return
      
      # Like each post
      liked = 0
      skipped = 0
      errors = 0
      
      # Get CSRF token
      csrf_token = None
      try:
        # Method 1: Read from Auth.json (saved by cookie-patreon.py)
        auth_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Configs", "Patreon", "Auth.json")
        with open(auth_path, "r", encoding="utf-8") as f:
          auth_data = json.load(f)
        csrf_token = auth_data.get("x-csrf-signature", "").strip()
        if csrf_token:
          self.log_msg(f"  ✅ CSRF from Auth.json: {csrf_token[:25]}...")
      except:
        pass
      
      if not csrf_token:
        # Method 2: Try fetching from HTML page
        try:
          self.log_msg("  Fetching CSRF from page...")
          page_headers = HEADERS.copy()
          page_headers["Accept"] = "text/html,application/xhtml+xml"
          csrf_resp = requests.get("https://www.patreon.com/home", headers=page_headers, impersonate="chrome")
          page_text = csrf_resp.text
          csrf_match = re.search(r'"csrfSignature"\s*:\s*"([^"]+)"', page_text)
          if csrf_match:
            csrf_token = csrf_match.group(1)
          if not csrf_token:
            csrf_match = re.search(r'csrf[_-]?signature["\\s:=]+([A-Za-z0-9_\-]{20,})', page_text)
            if csrf_match:
              csrf_token = csrf_match.group(1)
        except:
          pass
      
      if not csrf_token:
        self.log_msg("  ❌ No CSRF token! Add 'x-csrf-signature' to Auth.json manually.")
        self.log_msg("  How: Open DevTools > Network > click Like on any post >")
        self.log_msg("  copy 'x-csrf-signature' header value > paste in Auth.json")
        self.log_msg("  Or re-run cookie-patreon.py --auto to capture it.")
        return
      
      like_headers = HEADERS.copy()
      like_headers["Content-Length"] = "0"
      like_headers["Origin"] = "https://www.patreon.com"
      like_headers["x-csrf-signature"] = csrf_token
      
      for i, post_id in enumerate(all_post_ids):
        if log_manager.stop_requested:
          self.log_msg("  Stopped by user.")
          break
        
        like_url = f"https://www.patreon.com/api/posts/{post_id}/likes"
        like_params = {
          "fields[like]": "",
          "json-api-version": "1.0",
          "json-api-use-default-includes": "false"
        }
        
        try:
          resp = requests.post(like_url, headers=like_headers, params=like_params, impersonate="chrome")
          if resp.status_code == 201:
            liked += 1
          elif resp.status_code == 409 or resp.status_code == 400:
            skipped += 1
          elif resp.status_code == 429:
            self.log_msg(f"\n  ⛔ Rate limited by Patreon (429). Stopping.")
            self.log_msg(f"  Liked {liked} posts before getting throttled.")
            break
          else:
            errors += 1
            if errors <= 3:
              self.log_msg(f"  [!] Post {post_id}: HTTP {resp.status_code}")
        except Exception as e:
          errors += 1
        
        # Small delay to avoid rate limit (0.4s = ~150 likes/min)
        time.sleep(0.4)
        self.update_progress(i + 1, total, f"Liking: {liked} liked, {skipped} already")
      
      self.log_msg(f"\n  ✅ DONE: {liked} liked | {skipped} already liked | {errors} errors")
      self.update_progress(total, total, "Like Complete")
    except Exception as e:
      self.log_msg(f"Critical Error: {e}")
      import traceback
      traceback.print_exc()
    finally:
      self.call_from_thread(self.reset_ui)

  @on(Button.Pressed, "#btn_refresh")
  async def action_refresh(self): 
    await asyncio.sleep(0.1) 
    self.query_one(Log).clear()
    self.refresh_list()

if __name__ == '__main__':
  import importlib
  from colorama import Fore, Style, init as colorama_init
  colorama_init()
  
  print(f"{Fore.YELLOW}[*] Validating Patreon cookies...{Style.RESET_ALL}")
  
  try:
    test_url = "https://www.patreon.com/api/current_user?fields[user]=full_name&json-api-version=1.0"
    test_resp = requests.get(test_url, headers=HEADERS, impersonate="chrome")
    
    cookies_expired = False
    if test_resp.status_code == 401 or test_resp.status_code == 403:
      cookies_expired = True
    else:
      try:
        user_data = test_resp.json()
        name = user_data.get("data", {}).get("attributes", {}).get("full_name", "")
        if name:
          print(f"{Fore.GREEN}[*] Logged in as: {name}{Style.RESET_ALL}")
        elif not user_data.get("data"):
          cookies_expired = True
        else:
          print(f"{Fore.GREEN}[*] Cookies valid.{Style.RESET_ALL}")
      except:
        cookies_expired = True
    
    if cookies_expired:
      print(f"{Fore.RED}[!] Patreon cookies expired! Auto-refreshing...{Style.RESET_ALL}")
      try:
        cookie_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cookie-patreon.py")
        spec = importlib.util.spec_from_file_location("cookie_pt", cookie_path)
        cookie_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cookie_mod)
        result = cookie_mod.auto_scrape()
        if result:
          cookie_mod.save_auth(result.get("user-agent", ""), result.get("cookie", ""))
          print(f"{Fore.GREEN}[*] Cookies refreshed! Reloading...{Style.RESET_ALL}")
          HEADERS = create_auth()
        else:
          print(f"{Fore.RED}[!] Cookie scrape failed. Update Auth.json manually.{Style.RESET_ALL}")
      except Exception as e:
        print(f"{Fore.RED}[!] Auto-refresh failed: {e}{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}    Run the cookie scraper from the Hub.{Style.RESET_ALL}")
  except Exception as e:
    print(f"{Fore.YELLOW}[!] Cookie check skipped: {e}{Style.RESET_ALL}")
  
  print(f"{Fore.GREEN}[*] Starting Patreon TUI...{Style.RESET_ALL}")
  app = PatreonTUI()
  app.run()
