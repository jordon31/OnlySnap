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
from datetime import date
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from colorama import init, Fore, Style
system = platform.system()

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

# \TODO dynamically get app token
# Note: this is not an auth token
APP_TOKEN = "33d57ade8c02dbc5a333db99ff9ae26a"

# user info from /users/customer
USER_INFO = {}

# target profile
PROFILE = ""
# profile data from /users/<profile>
PROFILE_INFO = {}
PROFILE_ID = ""

def main_menu():
    options = {"1": "OnlyFans", "2": "Exit"}
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print("\nMenu:")
        for key, value in options.items():
            if value == "Exit":
                print(f"{key}) {Fore.RED}{value}{Fore.RESET}")
            elif value == "OnlyFans":
                print(f"{key}) {Fore.WHITE}Only{Fore.LIGHTBLUE_EX}Fans{Fore.RESET}")
            else:
                print(f"{key}) {value}")
        choice = input("Select an option: ")
        if choice.lower() in options.values() or choice in options.keys():
            if choice == "1" or choice.lower() == "onlyfans":
                os.system('cls' if os.name == 'nt' else 'clear')
                break 
            elif choice == "2" or choice.lower() == "exit":
                sys.exit()
        else:
            print("\nInvalid option, please try again.")
            input("\nPress Enter to continue...")

def assure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

def create_auth():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    auth_file_path = os.path.join(current_dir, "Configs", "OnlyFans", "Auth.json")

    with open(auth_file_path) as f:
        ljson = json.load(f)

    return {
        "Accept": "application/json, text/plain, */*",
        "User-Agent": ljson["user-agent"],
        "Accept-Encoding": "gzip, deflate",
        "user-id": ljson["user-id"],
        "x-bc": ljson["x-bc"],
        "Cookie": "sess=" + ljson["sess"],
        "app-token": APP_TOKEN
    }

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

def create_signed_headers(link, queryParams):
    global API_HEADER
    path = "/api2/v2" + link
    if (queryParams):
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
    return

def api_request(endpoint, getdata=None, postdata=None, getparams=None):
    if getparams == None:
        getparams = {
            "order": "publish_date_desc"
        }
    if getdata is not None:
        for i in getdata:
            getparams[i] = getdata[i]

    if postdata is None:
        create_signed_headers(endpoint, getparams)
        response = requests.get(URL + API_URL + endpoint,
                                headers=API_HEADER,
                                params=getparams)

        num_posts = len(response.json()) if isinstance(response.json(), list) else 0

        if endpoint == "/chats/" + PROFILE_ID + "/messages":
            return response.json()
            
        if getdata is not None:
            list_base = response.json()
            posts_num = len(list_base)

            MAX_LIMIT = 999999
            if posts_num >= MAX_LIMIT:
                beforePublishTime = list_base[MAX_LIMIT - 1]['postedAtPrecise']
                getparams['beforePublishTime'] = beforePublishTime

                while posts_num == MAX_LIMIT:
                    create_signed_headers(endpoint, getparams)
                    list_extend = requests.get(URL + API_URL + endpoint,
                                               headers=API_HEADER,
                                               params=getparams).json()
                    posts_num = len(list_extend)
                    list_base.extend(list_extend)

                    if posts_num < MAX_LIMIT:
                        break

                    beforePublishTime = list_extend[posts_num - 1]['postedAtPrecise']
                    getparams['beforePublishTime'] = beforePublishTime

            return list_base
        else:
            return response
    else:
        create_signed_headers(endpoint, getparams)
        response_post = requests.post(URL + API_URL + endpoint,
                                      headers=API_HEADER,
                                      params=getparams,
                                      data=postdata)
        
        num_posts_post = len(response_post.json()) if isinstance(response_post.json(), list) else 0
        
        return response_post

def get_highlight_details_API(highlight_id):
    endpoint = f"/stories/highlights/{highlight_id}"
    create_signed_headers(endpoint, {})
    response = requests.get(URL + API_URL + endpoint, headers=API_HEADER, params={})
    return response.json() if response.status_code == 200 else {}

# /users/<profile>
# get information about <profile>
# <profile> = "customer" -> info about yourself
def get_user_info(profile):
    info = api_request("/users/" + profile).json()
    if "error" in info:
        print("\nERROR: " + info["error"]["message"])
        time.sleep(4)
        exit()

    return info 

# to get subscribesCount for displaying all subs
# info about yourself
def user_me():
    me = api_request("/users/me").json()
    if "error" in me:
        print("\nERROR: " + me["error"]["message"])
        time.sleep(4)
        exit()
    return me

def save_to_cache(data):
    assure_dir(CACHE_DIR)
    with open(CACHE_FILE, 'w') as f:
        json.dump(data, f)

def load_from_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    return None

# get all subscriptions in json
def get_subs():
    total_subs = load_from_cache()
    
    if total_subs is None:
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
            
            subscriptions = api_request("/subscriptions/subscribes", getparams=params).json()
            
            if not subscriptions:
                break
                
            for sub in subscriptions:
                if 'currentSubscribePrice' in sub and sub['currentSubscribePrice'] == 0:
                    sub['type'] = 'Free'
                    # Check if user has a trial subscription
                    for subscribe in sub['subscribedByData']['subscribes']:
                        if 'type' in subscribe and subscribe['type'] == 'trial':
                            sub['type'] = 'Trial'
                else:
                    sub['type'] = 'Payed'
            
            total_subs.extend(subscriptions)
            offset += SUB_LIMIT
        
        save_to_cache(total_subs)

    return total_subs

def search_profiles(query):
    filtered_profiles = {key: value for key, value in sub_dict.items() if query.lower() in value.lower()}
    return filtered_profiles

new_files = 0

if len(sys.argv) == 2:
    ARG1 = sys.argv[1]
else:
    ARG1 = ""

def select_sub():
    SUBS = get_subs()
    ALL_LIST = []
    for i in range(1, len(SUBS) + 1):
        ALL_LIST.append(i)
    sub_type_dict = {} 
    for i in range(0, len(SUBS)):
        sub_dict.update({i + 1: SUBS[i]['username']})
        sub_type_dict.update({i + 1: SUBS[i]['type']})

    if len(sub_dict) == 0:
        print('No models subbed')
        time.sleep(4)
        exit()

    subscribes_count = user_me()["subscribesCount"]
    
    prompt_text = f"Sub Active: {subscribes_count}\n\nEnter the profile name to download (use TAB to see the full list):\n\n"
    
    username_list = [f"{value} -- {sub_type_dict[key]}" for key, value in sub_dict.items()] 

    if ARG1 == "--all":
        print("Downloading media from all profiles...")
        return ALL_LIST

    username_list.insert(0, "*** Download All Models ***")
    username_completer = WordCompleter(username_list, ignore_case=True)

    MODELS = prompt(prompt_text, completer=username_completer)
    
    if MODELS == "*** Download All Models ***":
        print("Downloading media from all profiles...")
        return ALL_LIST

    selected_models = [key for key, value in sub_dict.items() if f"{value} -- {sub_type_dict[key]}" == MODELS]

    if len(selected_models) == 0:
        print("No matching profiles found.")
        time.sleep(2)
        print("\033[2J\033[H")
        return select_sub()
    elif len(selected_models) == 1:
        return selected_models
    else:
        print("Error: Multiple matching profiles found.")
        time.sleep(2)
        print("\033[2J\033[H")
        return select_sub()

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
        file_type = re.findall("\.\w+", source)[-1]
        path = "/" + public_file + file_type
        full_path = "Profiles/" + PROFILE + "/Public" + path
        if not os.path.isfile(full_path):
            download_file(PROFILE_INFO[public_file], full_path)
            global new_files
            new_files += 1

def get_year_folder(timestamp, media_type):
    config_path = os.path.join('Configs', 'OnlyFans', 'Config.json')
    with open(config_path, 'r') as f:
        settings = json.load(f)

    if settings['settings']['no_year_folders']:
        folder_name = ""
    else:
        today = dt.date.today()
        yesterday = today - dt.timedelta(days=1)
        last_week = today - dt.timedelta(days=7)
        post_date = timestamp.date()
        if post_date == today:
            folder_name = "Today"
        elif post_date == yesterday:
            folder_name = "Yesterday"
        elif post_date > last_week:
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
        photo_path = base_path + "/!Photos/" + folder_name
        assure_dir(photo_path)
    elif media_type == "video":
        video_path = base_path + "/!Videos/" + folder_name
        assure_dir(video_path)

    return folder_name

def get_year_path(post_date):
    post_year = post_date.year
    folder_prefix = str(post_year)
    return folder_prefix

# download a media item and save it to the relevant directory
def download_media(media, is_archived, path=None, timestamp=None, is_stream=False, source_url=None):
    global new_files
    id = str(media["id"])
    source = source_url if source_url else media["source"]["source"]

    if (media["type"] != "photo" and media["type"] != "video" and media["type"] != "gif") or not media['canView']:
        return False

    ext = re.findall('\.\w+\?', source)
    if len(ext) == 0:
        return False
    ext = ext[0][:-1]

    if media["type"] == "gif":
        type = "video"
    else:
        type = media["type"]

    if path is None:
        if is_stream:
            path = "/Media/Streams/"
        else:
            if is_archived:
                path = "/Media/Archived/"
                if type == "photo":
                    path += "Photos/"
                else:
                    path += "Videos/"
            else:
                folder_name = get_year_folder(timestamp, type)
                path = "/Media/"
                if type == "photo":
                    path += "!Photos/" + folder_name + "/"
                else:
                    path += "!Videos/" + folder_name + "/"
        path += id + ext
        path = "Profiles/" + PROFILE + path
    else:
        path = path + id + ext

    if media["type"] == "video" and not is_stream:
        stream_path = "Profiles/" + PROFILE + "/Media/Streams/" + id + ext
        if os.path.isfile(stream_path):
            return False

    if not os.path.isfile(path):
        new_files += 1
        download_file(source, path, timestamp)
        return True

    return False

# helper to generally download files
def download_file(source, path, timestamp=None):
    assure_dir(os.path.dirname(path))
    r = requests.get(source, stream=True)
    with open(path, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)

    if timestamp is not None:
        set_file_mtime(path, timestamp)

def get_id_from_path(path):
    last_index = path.rfind("/")
    second_last_index = path.rfind("/", 0, last_index - 1)
    id = path[second_last_index + 1:last_index]
    return id

def download_posts(posts, is_archived, pbar, is_stream=False):
    media_downloaded = 0
        
    config = load_config()
    save_text_with_media = not config['settings']['disable_download_post_with_txt']
    download_tagged_posts = config['settings']['download_tagged_posts']
    merge_tagged_media = config['settings']['merge_tagged_media']

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []
        for post in posts:
            # Fix here: First check if 'text' exists in post, then perform the check for tags.
            contains_tags = any(tag in post.get("text", "").lower() for tag in ["@", "#adv", "#ad"])
            
            if "text" in post and post["text"] is not None and not download_tagged_posts and contains_tags:
                continue  # Skip this post if we don't want to download tagged posts
                
            if not download_tagged_posts and "spin" in post.get("text", "").lower():
                continue

            if "media" not in post or ("canViewMedia" in post and not post["canViewMedia"]):
                continue
                
            post_timestamp_unix = float(post["postedAtPrecise"])
            post_timestamp = dt.datetime.fromtimestamp(post_timestamp_unix)
            post_date_str = post_timestamp.strftime('%Y-%m-%dT%H_%M_%S')
            
            for media in post["media"]:
                if 'source' in media and isinstance(media["source"]["source"], str):
                    id = str(media["id"])
                    source = media["source"]["source"]
                    ext = re.findall('\.\w+\?', source)
                    if len(ext) == 0:
                        continue
                    ext = ext[0][:-1]
                    type = media["type"] if media["type"] != "gif" else "video"

                    # If it's a tagged post, adjust the path accordingly
                    if download_tagged_posts and contains_tags:
                        base_path = f"Profiles/{PROFILE}/Media/Tag-Post"
                        if not merge_tagged_media:
                            path = f"{base_path}/{type}s/"
                        else:
                            path = f"{base_path}/"
                        assure_dir(path)  # Make sure the directory exists
                    elif save_text_with_media:
                        post_dir = f"Profiles/{PROFILE}/Media/Posts/{post_date_str}"
                        assure_dir(post_dir)
                        
                        if "text" in post and post.get("text"):
                            text_file_path = f"{post_dir}/_text.txt"
                            with open(text_file_path, "w", encoding='utf-8') as f:
                                f.write(post["text"])
                        
                        path = f"{post_dir}/"
                    else:
                        path = None
                    
                    futures.append(executor.submit(download_media, media, is_archived, path, post_timestamp, is_stream))
                
        for future in as_completed(futures):
            was_downloaded = future.result()
            if was_downloaded:
                media_downloaded += 1
                pbar.update(1)
                
    return media_downloaded

def clean_filename(filename):
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    for char in invalid_chars:
        filename = filename.replace(char, '')
    return filename
    
def download_highlights(highlights):
    if not highlights["list"]:
        return

    disable_cover_highlights = CONFIG["settings"]["disable_cover_highlights"]
    disable_folder_highlights = CONFIG["settings"]["disable_folder_highlights"]

    assure_dir("Profiles/" + PROFILE + "/Media/Highlights")
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        futures = []
        
        for highlight in highlights["list"]:
            title = clean_filename(highlight.get("title", "Untitled"))
            highlight_id = highlight.get("id", None)
            if highlight_id:
                highlight_details = get_highlight_details_API(highlight_id)
                path = f"Profiles/{PROFILE}/Media/Highlights/"
                if not disable_folder_highlights:
                    path += f"{title}/"
                    assure_dir(path)

                cover_url = highlight.get("cover", None)
                if cover_url and not disable_cover_highlights:
                    cover_path = path + "!cover.jpg"
                    download_file(cover_url, cover_path)

                stories = highlight_details.get("stories", [])
                for story in stories:
                    media_items = story.get("media", [])
                    for media_item in media_items:
                        source_url = media_item["files"]["source"]["url"]
                        futures.append(executor.submit(download_media, media_item, False, path=path, source_url=source_url))

        for future in as_completed(futures):
            future.result()

def download_chats(chats):
    if not isinstance(chats, list):
        return

    photos_to_download = []
    videos_to_download = []

    for chat in chats:
        if not isinstance(chat, dict):
            continue
            
        text = chat.get("text", "")
        if "#adv" in text.lower() or "#ad" in text.lower() or "spin" in text.lower():
            continue

        media_items = chat.get("media", [])
        for media_item in media_items:
            media_type = media_item["type"]
            source_url = media_item.get("src") or media_item.get("source", {}).get("source")
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
                source_url = media_item["files"]["source"]["url"]
                futures.append(executor.submit(download_media, media_item, False, path="Profiles/" + PROFILE + "/Media/Stories/", source_url=source_url))

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
                videos.extend(extra_video_posts)
            
            has_more_videos = any(len(future.result()) > 0 for future in futures)
    return videos

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
    highlights = fetch_all_highlights()
    download_highlights({"list": highlights})
    return {"list": highlights}

def get_all_stories():
    stories = api_request("/users/" + PROFILE_ID + "/stories", getdata={"limit": "999999"})
    download_stories(stories)
    return stories

def get_all_chats():
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

        download_chats(chats)

        last_id = chats[-1].get("id")

def count_files(posts):
    count = 0
    for post in posts:
        if "media" not in post or ("canViewMedia" in post and not post["canViewMedia"]):
            continue
        count += len(post["media"])
    return count

def live_print(message, delay=0.01):
    for char in message:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()

if __name__ == "__main__":
    if ARG1 != "--all":
        main_menu()

    print(Fore.WHITE + "\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    live_print("~  " + Fore.WHITE + "Welcome on " + Fore.WHITE + "Only" + Fore.LIGHTBLUE_EX + "Snap" + Fore.WHITE + " scraper! ~")
    live_print("~  Telegram: @BrahGirl ~")
    print(Fore.LIGHTBLUE_EX + "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~" + Style.RESET_ALL + "\n")

    if len(sys.argv) != 2:
        ARG1 = ""
    else:
        ARG1 = sys.argv[1]

    dynamic_rules = requests.get(
        'https://raw.githubusercontent.com/DIGITALCRIMINALS/dynamic-rules/main/onlyfans.json').json()

    API_HEADER = create_auth()

while True:  
    try: 
        sub_dict = {}
        SELECTED_MODELS = select_sub()

        for M in SELECTED_MODELS:
            new_files = 0
            PROFILE = sub_dict[int(M)]
            time.sleep(3)
            os.system('cls' if os.name == 'nt' else 'clear')
            PROFILE_INFO = get_user_info(PROFILE)
            PROFILE_ID = str(PROFILE_INFO["id"])

            print("\nThe content is being downloaded to the profiles/" + PROFILE + " directory.\n")

            if os.path.isdir("Profiles/" + PROFILE):
                print("\nThe folder profiles/" + PROFILE + " exists.")
                print("Media already present will not be re-downloaded.")

            assure_dir("Profiles")
            assure_dir("Profiles/" + PROFILE)
            assure_dir("Profiles/" + PROFILE + "/Public")

            # first save profile info
            print("Saving profile info...")

            sinf = {
                "id": PROFILE_INFO["id"],
                "name": PROFILE_INFO["name"],
                "username": PROFILE_INFO["username"],
                "about": PROFILE_INFO["rawAbout"],
                "joinDate": PROFILE_INFO["joinDate"],
                "website": PROFILE_INFO["website"],
                "wishlist": PROFILE_INFO["wishlist"],
                "location": PROFILE_INFO["location"],
                "lastSeen": PROFILE_INFO["lastSeen"]
            }
            if sinf["joinDate"] is not None:
                sinf["joinDate"] = datetime.datetime.strptime(sinf["joinDate"], "%Y-%m-%dT%H:%M:%S+00:00").strftime("%Y-%m-%d")
            if sinf["lastSeen"] is not None:
                sinf["lastSeen"] = datetime.datetime.strptime(sinf["lastSeen"], "%Y-%m-%dT%H:%M:%S+00:00").strftime("%Y-%m-%d - TIME: %H:%M")

            sinf = {k: v for k, v in sinf.items() if v is not None}
            for key, value in sinf.items():
                if isinstance(value, str):
                    sinf[key] = value.replace("\n", "")

            with open("Profiles/" + PROFILE + "/info.json", 'w', encoding='utf-8') as infojson:  
                json.dump(sinf, infojson, ensure_ascii=False, indent=4, sort_keys=True)
                infojson.close()
                shutil.move("Profiles/" + PROFILE + "/info.json", "Profiles/" + PROFILE + "/Dump.json")

                download_public_files()

                # get all user posts
                print("Finding photos...", end=' ', flush=True)
                print()
                photos = api_request("/users/" + PROFILE_ID + "/posts/photos", getdata={"limit": "999999"})
                photo_posts = get_all_photos(photos)
                print("Finding videos...", end=' ', flush=True)
                print()
                videos = api_request("/users/" + PROFILE_ID + "/posts/videos", getdata={"limit": "999999"})
                video_posts = get_all_videos(videos)
                print("Finding archived content...", end=' ', flush=True)
                print()
                streams = api_request("/users/" + PROFILE_ID + "/posts/streams", getdata={"limit": "999999"})
                stream_posts = get_all_streams(streams)
                archived_posts_initial = api_request("/users/" + PROFILE_ID + "/posts/archived", getdata={"limit": "999999"})
                archived_posts = get_all_archived(archived_posts_initial)
                ################################################
                extra_img_posts = api_request("/users/" + PROFILE_ID + "/posts/photos", getdata={"limit": "999999"})
                extra_video_posts = api_request("/users/" + PROFILE_ID + "/posts/videos", getdata={"limit": "999999"})
                ################################################
                postcount = len(photo_posts) + len(video_posts) + len(extra_img_posts) + len(extra_video_posts)
                archived_postcount = len(archived_posts)
                
                if postcount + archived_postcount == 0:
                   print("ERROR: 0 posts found.")
                   time.sleep(4)
                   exit()
                has_photos = len(photo_posts) > 0
                has_videos = len(video_posts) > 0
                has_archived = len(archived_posts) > 0
                has_stream = len (stream_posts) > 0

                config = load_config()
                disable_download_post_with_txt = not config['settings']['disable_download_post_with_txt']

                if has_photos or has_videos or has_archived or has_stream:  
                    assure_dir("Profiles/" + PROFILE + "/Media")
    
                    if not disable_download_post_with_txt:
                        if has_photos:
                            assure_dir("Profiles/" + PROFILE + "/Media/!Photos")
                        if has_videos:
                            assure_dir("Profiles/" + PROFILE + "/Media/!Videos")
                        if has_stream:
                            assure_dir("Profiles/" + PROFILE + "/Media/Streams")
                        if has_archived:
                            assure_dir("Profiles/" + PROFILE + "/Media/Archived")
                            if len([post for post in archived_posts if any(media['type'] == 'photo' for media in post.get('media', []))]) > 0:
                                assure_dir("Profiles/" + PROFILE + "/Media/Archived/Photos")
                            if len([post for post in archived_posts if any(media['type'] == 'video' for media in post.get('media', []))]) > 0:
                                assure_dir("Profiles/" + PROFILE + "/Media/Archived/Videos")
                else:
                    print("No photos, videos, or archives found. Skipping folder creation.")
                    continue

                total_count = count_files(photo_posts) + count_files(video_posts) + count_files(archived_posts)

                starttime = time.time()
                os.system('cls' if os.name == 'nt' else 'clear') 

                media_count = 0
                new_files = 0
                with tqdm(total=new_files, desc="Downloading", ncols=80, unit=" files", leave=False) as pbar:

                    highlights = get_all_highlights() #no count
                    download_highlights(highlights)

                    stories = get_all_stories() #no count
                    download_stories(stories)

                    chats = get_all_chats() #no count
                    download_chats(chats)

                    media_downloaded = download_posts(photo_posts, False, pbar) 
                    media_count += media_downloaded

                    media_downloaded = download_posts(extra_img_posts, False, pbar)
                    media_count += media_downloaded

                    media_downloaded = download_posts(stream_posts, False, pbar, is_stream=True)
                    media_count += media_downloaded

                    media_downloaded = download_posts(video_posts, False, pbar)
                    media_count += media_downloaded

                    media_downloaded = download_posts(archived_posts, True, pbar)
                    media_count += media_downloaded

                    media_downloaded = download_posts(extra_video_posts, False, pbar)
                    media_count += media_downloaded
                    
                print("\nDOWNLOADED " + str(new_files) + " NEW FILES\n")
                if len(SELECTED_MODELS) > 1:
                    user_choice = 'c'
                    time.sleep(2)
                else:
                    user_choice = ''
                    while user_choice not in ['c', 'q']:
                        user_choice = input("\nPress 'c' to continue with another user or 'q' to exit: ").lower()
                if user_choice == 'q':
                    sys.exit()
                elif user_choice == 'c':
                    os.system('cls' if os.name == 'nt' else 'clear')
    except Exception as e:
            print(f"\nAn error has occurred: {e}\n{traceback.format_exc()}")
            print("Please try again.")
