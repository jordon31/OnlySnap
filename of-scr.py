import re
import os
import sys
import json
import shutil
import requests
import time
import datetime as dt
import hashlib
import emoji
import traceback
import datetime
import ctypes
import platform
from datetime import date
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from colorama import init, Fore, Style

system = platform.system()

if system == "Windows":
    ctypes.windll.kernel32.SetConsoleTitleW("OF-SCR") #Title Application Windows
elif system == "Darwin":  # macOS
    sys.stdout.write(f"\x1b]2;{'OF-SCR'}\x07") #Title Application MAC
    sys.stdout.flush()
else:
    sys.stdout.write(f"\033]0;{'OF-SCR'}\a") #TItle Application Linux
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

# helper function to make sure a dir is present
def assure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path, exist_ok=True)

# Create Auth with Json
def create_auth():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    auth_file_path = os.path.join(current_dir, "auth.json")

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

# Every API request must be signed
def create_signed_headers(link, queryParams):
    global API_HEADER
    path = "/api2/v2" + link
    if (queryParams):
        query = '&'.join('='.join((key, val)) for (key, val) in queryParams.items())
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

# API request convenience function
# getdata and postdata should both be JSON
def api_request(endpoint, getdata=None, postdata=None, getparams=None):
    if getparams == None:
        getparams = {
            "order": "publish_date_desc"
        }
    if getdata is not None:
        for i in getdata:
            getparams[i] = getdata[i]

    if postdata is None:
        if getdata is not None:
            
            create_signed_headers(endpoint, getparams)
            list_base = requests.get(URL + API_URL + endpoint,
                                     headers=API_HEADER,
                                     params=getparams).json()
            posts_num = len(list_base)

            # Remove Limit
            MAX_LIMIT = 999999
            if posts_num >= MAX_LIMIT:
                beforePublishTime = list_base[MAX_LIMIT - 1]['postedAtPrecise']
                getparams['beforePublishTime'] = beforePublishTime

                while posts_num == MAX_LIMIT:
                    # Extract posts
                    create_signed_headers(endpoint, getparams)
                    list_extend = requests.get(URL + API_URL + endpoint,
                                               headers=API_HEADER,
                                               params=getparams).json()
                    posts_num = len(list_extend)
                    # Merge with previous posts
                    list_base.extend(list_extend)

                    if posts_num < MAX_LIMIT:
                        break

                    # Re-add again the updated beforePublishTime/postedAtPrecise params
                    beforePublishTime = list_extend[posts_num - 1]['postedAtPrecise']
                    getparams['beforePublishTime'] = beforePublishTime

            return list_base
        else:
            create_signed_headers(endpoint, getparams)
            #print('x')
            return requests.get(URL + API_URL + endpoint,
                                headers=API_HEADER,
                                params=getparams)
    else:
        create_signed_headers(endpoint, getparams)
        return requests.post(URL + API_URL + endpoint,
                             headers=API_HEADER,
                             params=getparams,
                             data=postdata)

# /users/<profile>
# get information about <profile>
# <profile> = "customer" -> info about yourself
def get_user_info(profile):
    info = api_request("/users/" + profile).json()
    if "error" in info:
        print("\nERROR: " + info["error"]["message"])
        # bail, we need info for both profiles to be correct
        exit()

    #total_photos = info.get("photosCount", 0)
    #total_videos = info.get("videosCount", 0) 

    return info 

# to get subscribesCount for displaying all subs
# info about yourself
def user_me():
    me = api_request("/users/me").json()
    if "error" in me:
        print("\nERROR: " + me["error"]["message"])
        # bail, we need info for both profiles to be correct
        exit()
    return me

# get all subscriptions in json
def get_subs():
    SUB_LIMIT = str(user_me()["subscribesCount"])
    params = {
        "type": "active",
        "sort": "desc",
        "field": "expire_date",
        "limit": SUB_LIMIT
    }
    subscriptions = api_request("/subscriptions/subscribes", getparams=params).json()
    # Add a new field 'is_free' to each subscription
    for sub in subscriptions:
        if 'currentSubscribePrice' in sub and sub['currentSubscribePrice'] == 0:
            sub['type'] = 'Free'
        else:
            sub['type'] = 'Payed'
    return subscriptions


def search_profiles(query):
    filtered_profiles = {key: value for key, value in sub_dict.items() if query.lower() in value.lower()}
    return filtered_profiles

# download public files like avatar and header
new_files = 0

def select_sub():

    SUBS = get_subs()
    ALL_LIST = []
    for i in range(1, len(SUBS)+1):
        ALL_LIST.append(i)
    sub_type_dict = {}  # new dictionary for subscription types
    for i in range(0, len(SUBS)):
        sub_dict.update({i+1: SUBS[i]['username']})
        sub_type_dict.update({i+1: SUBS[i]['type']})

    if len(sub_dict) == 1:
        print('No models subbed')
        exit()

    # Select Model
    if ARG1 == "all":
        return ALL_LIST

    # Create a list of full usernames for autocomplete
    username_list = [f"{value} -- {sub_type_dict[key]}" for key, value in sub_dict.items()]  # use sub_type_dict here
    username_list.insert(0, "*** Download All Models ***")
    username_completer = WordCompleter(username_list, ignore_case=True)

    # Use the prompt() function to allow the user to select a template with autocomplete
    MODELS = prompt("\nEnter the profile name to download (use TAB for to see the full list):\n\n", completer=username_completer)
    if MODELS == "*** Download All Models ***":
        return ALL_LIST
        
    selected_models = [key for key, value in sub_dict.items() if f"{value} -- {sub_type_dict[key]}" == MODELS]  # use sub_type_dict here

    if len(selected_models) == 0:
        print("No matching profiles found.")
        time.sleep(2)
        print("\033[2J\033[H") # Clear console
        return select_sub()
    elif len(selected_models) == 1:
        return selected_models
    else:
        print("Error: Multiple matching profiles found.")
        time.sleep(2)
        print("\033[2J\033[H") # Clear console
        return select_sub()

#FIX TIME
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
        path = "/" + public_file + file_type  # removed id from the path
        if not os.path.isfile("profiles/" + PROFILE + "/Public" + path):  # added "/Public" to the path
            download_file(PROFILE_INFO[public_file], "/Public" + path)
            global new_files
            new_files += 1
            
def get_year_folder(timestamp, media_type):
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
        folder_name = str(year)
    
    base_path = "profiles/" + PROFILE + "/Media"
    if media_type == "photo":
        photo_path = base_path + "/photos/" + folder_name
        assure_dir(photo_path)
    elif media_type == "video":
        video_path = base_path + "/videos/" + folder_name
        assure_dir(video_path)

    return folder_name

def get_year_path(post_date):
    post_year = post_date.year
    folder_prefix = str(post_year)
    return folder_prefix

# download a media item and save it to the relevant directory
def download_media(media, is_archived, timestamp=None):
    global new_files
    id = str(media["id"])
    source = media["source"]["source"]

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

    if is_archived:
        path = "/Media/archived/"
        if type == "photo":
            path += "photos/"
        else:
            path += "videos/"
    else:
        folder_name = get_year_folder(timestamp, type)
        path = "/Media/"
        if type == "photo":
            path += "photos/" + folder_name + "/"
        else:
            path += "videos/" + folder_name + "/"

    path += id + ext

    if not os.path.isfile("profiles/" + PROFILE + path):
        new_files += 1  # increment the count of new files
        download_file(source, path, timestamp)
        return True
    return False

    path += id + ext

    if not os.path.isfile("profiles/" + PROFILE + path):
        new_files += 1  # increment the count of new files
        download_file(source, path, timestamp)
        return True
    return False

# helper to generally download files
def download_file(source, path, timestamp=None):
    r = requests.get(source, stream=True)
    with open("profiles/" + PROFILE + path, 'wb') as f:
        r.raw.decode_content = True
        shutil.copyfileobj(r.raw, f)

    if timestamp is not None:
        set_file_mtime("profiles/" + PROFILE + path, timestamp)

def get_id_from_path(path):
    last_index = path.rfind("/")
    second_last_index = path.rfind("/", 0, last_index - 1)
    id = path[second_last_index + 1:last_index]
    return id

def calc_process_time(starttime, arraykey, arraylength):
    timeelapsed = time.time() - starttime
    timeest = (timeelapsed / arraykey) * (arraylength)
    finishtime = starttime + timeest
    finishtime = dt.datetime.fromtimestamp(finishtime).strftime("%H:%M:%S")  # in time
    lefttime = dt.timedelta(seconds=(int(timeest - timeelapsed)))  # get a nicer looking timestamp this way
    timeelapseddelta = dt.timedelta(seconds=(int(timeelapsed)))  # same here
    return (timeelapseddelta, lefttime, finishtime)

# iterate over posts, downloading all media
# returns the new count of downloaded posts
def download_posts(posts, is_archived, pbar):
    media_downloaded = 0
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for post in posts:
            if "text" in post and post["text"] is not None and ("@" in post["text"].lower() or "#adv" in post["text"].lower() or "#ad" in post["text"].lower()):
                continue

            if "media" not in post or ("canViewMedia" in post and not post["canViewMedia"]):
                continue

            post_timestamp_unix = float(post["postedAtPrecise"])
            post_timestamp = dt.datetime.fromtimestamp(post_timestamp_unix)

            for media in post["media"]:
                if 'source' in media and isinstance(media["source"]["source"], str):
                    id = str(media["id"])
                    source = media["source"]["source"]
                    ext = re.findall('\.\w+\?', source)
                    if len(ext) == 0:
                        continue
                    ext = ext[0][:-1]
                    if media["type"] == "gif":
                        type = "video"
                    else:
                        type = media["type"]
                    if is_archived:
                        path = "/archived/"
                        if type == "photo":
                            path += "photos/"
                        else:
                            path += "videos/"
                    else:
                        folder_name = get_year_folder(post_timestamp, type)
                        path = "/"
                        if type == "photo":
                            path += "photos/" + folder_name + "/"
                        else:
                            path += "videos/" + folder_name + "/"
                    path += id + ext
                    if os.path.isfile("profiles/" + PROFILE + path):
                        continue
                    futures.append(executor.submit(download_media, media, is_archived, timestamp=post_timestamp))

        for future in as_completed(futures):
            was_downloaded = future.result()
            if was_downloaded:
                media_downloaded += 1
                pbar.update(1)

    return media_downloaded

def get_all_videos(videos):
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = []
        len_vids = len(videos)
        has_more_videos = len_vids > 0

        while has_more_videos:
            len_vids = len(videos)
            future = executor.submit(
                api_request,
                "/users/" + PROFILE_ID + "/posts/videos",
                getdata={"limit": "999999", "order": "publish_date_desc", "beforePublishTime": videos[len_vids - 1]["postedAtPrecise"]},
            )
            extra_video_posts = future.result()
            videos.extend(extra_video_posts)
            has_more_videos = len(extra_video_posts) > 0

    return videos

def get_all_photos(images):
    with ThreadPoolExecutor(max_workers=14) as executor:
        futures = []
        len_imgs = len(images)
        has_more_images = len_imgs > 0

        while has_more_images:
            len_imgs = len(images)
            future = executor.submit(
                api_request,
                "/users/" + PROFILE_ID + "/posts/photos",
                getdata={"limit": "999999", "order": "publish_date_desc", "beforePublishTime": images[len_imgs - 1]["postedAtPrecise"]},
            )
            extra_img_posts = future.result()
            images.extend(extra_img_posts)
            has_more_images = len(extra_img_posts) > 0

    return images

def count_files(posts):
    count = 0
    for post in posts:
        if "media" not in post or ("canViewMedia" in post and not post["canViewMedia"]):
            continue
        count += len(post["media"])
    return count

def live_print(message, delay=0.03):
    for char in message:
        print(char, end='', flush=True)
        time.sleep(delay)
    print()  # New line after message

if __name__ == "__main__":
    main_menu()

    print(Fore.WHITE + "\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~")
    live_print("~  " + Fore.WHITE + "Welcome on " + Fore.WHITE + "Only" + Fore.LIGHTBLUE_EX + "Fans" + Fore.WHITE + " scraper! ~")
    live_print("~  Telegram: @BrahGirl ~")
    print(Fore.LIGHTBLUE_EX + "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~" + Style.RESET_ALL + "\n")

    # Gather inputs
    if len(sys.argv) != 2:
        ARG1 = ""
    else:
        ARG1 = sys.argv[1]

    # Get the rules for the signed headers dynamically, as they may be fluid
    dynamic_rules = requests.get(
        'https://raw.githubusercontent.com/DIGITALCRIMINALS/dynamic-rules/main/onlyfans.json').json()
    # Create Header
    API_HEADER = create_auth()

    # Select sub
while True:  
    try: 
        # Select sub
        sub_dict = {}
        SELECTED_MODELS = select_sub()

        # start process
        for M in SELECTED_MODELS:
            new_files = 0
            PROFILE = sub_dict[int(M)]
            time.sleep(3)
            os.system('cls' if os.name == 'nt' else 'clear')
            PROFILE_INFO = get_user_info(PROFILE)
            PROFILE_ID = str(PROFILE_INFO["id"])

            print("\nThe content is being downloaded to the profiles/" + PROFILE + " directory.\n")
            #print(f"Total Photos: {total_photos}")
            #print(f"Total Videos: {total_videos}")

            if os.path.isdir("profiles/" + PROFILE):
                print("\nThe folder profiles/" + PROFILE + " exists.")
                print("Media already present will not be re-downloaded.")

            assure_dir("profiles")
            assure_dir("profiles/" + PROFILE)
            assure_dir("profiles/" + PROFILE + "/Public")

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

            emoji_pattern = re.compile("["
            u"\U0001F000-\U0001F6FF"  # emoticons
            u"\U0001F700-\U0001F77F"  # dingbats
            u"\U0001F780-\U0001F7FF"  # geometric shapes
            u"\U0001F800-\U0001F8FF"  # miscellaneous symbols
            u"\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
            u"\U0001FA00-\U0001FA6F"  # sports and activities
            u"\U0001FA70-\U0001FAFF"  # food and drink
            u"\U00002702-\U000027B0"  # other miscellaneous symbols
            u"\U00002700-\U00002702"  # dingbats
            u"\u200d"                 # zero-width joiner
            u"\u2019"                 # '
            u"\ufe0f"                 # VS16
            u"\u2640-\u2642"          # gender symbols
            u"\u2600-\u26FF"          # miscellaneous symbols
            u"\u2700-\u27BF"          # dingbats
            "]+", flags=re.UNICODE)

            about_clean = emoji_pattern.sub(lambda x: '', sinf['about'])
            about_clean = about_clean.replace('\n\n', '').replace('\n', '')

            sinf['about'] = about_clean
            sinf = {k: v for k, v in sinf.items() if v is not None}

            with open("profiles/" + PROFILE + "/info.json", 'w') as infojson:  

                json.dump(sinf, infojson, indent=4, sort_keys=True)
                infojson.close()
                shutil.move("profiles/" + PROFILE + "/info.json", "profiles/" + PROFILE + "/Dump.json")

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
                archived_posts = api_request("/users/" + PROFILE_ID + "/posts/archived", getdata={"limit": "999999"})
                #print("API response: ", archived_posts)
                #messages_posts = api_request("/chats/" + PROFILE_ID + "/messages", getparams={"limit": "999999"})
                ################################################
                extra_img_posts = api_request("/users/" + PROFILE_ID + "/posts/photos", getdata={"limit": "999999"})
                extra_video_posts = api_request("/users/" + PROFILE_ID + "/posts/videos", getdata={"limit": "999999"})
                ################################################
                postcount = len(photo_posts) + len(video_posts) + len(extra_img_posts) + len(extra_video_posts)
                archived_postcount = len(archived_posts)
                
                if postcount + archived_postcount == 0:
                   print("ERROR: 0 posts found.")
                   exit()
                has_photos = len(photo_posts) > 0
                has_videos = len(video_posts) > 0
                has_archived = len(archived_posts) > 0

                if has_photos or has_videos or has_archived:  
                    assure_dir("profiles/" + PROFILE + "/Media")
                    if has_photos:
                        assure_dir("profiles/" + PROFILE + "/Media/Photos")
                    if  has_videos:
                        assure_dir("profiles/" + PROFILE + "/Media/Videos")
                    if  has_archived:
                        assure_dir("profiles/" + PROFILE + "/Media/Archived")
                        if has_photos:
                           assure_dir("profiles/" + PROFILE + "/Media/Archived/Photos")
                        if has_videos:
                           assure_dir("profiles/" + PROFILE + "/Media/Archived/Videos")
                else:
                    print("No photos, videos, or archives found. Skipping folder creation.")
                    continue

                total_count = count_files(photo_posts) + count_files(video_posts) + count_files(archived_posts)

                starttime = time.time()
                os.system('cls' if os.name == 'nt' else 'clear') 

                media_count = 0
                new_files = 0
                with tqdm(total=new_files, desc="Downloading", ncols=80, unit=" files", leave=False) as pbar:
                    media_downloaded = download_posts(photo_posts, False, pbar)
                    media_count += media_downloaded

                    media_downloaded = download_posts(video_posts, False, pbar)
                    media_count += media_downloaded

                    media_downloaded = download_posts(archived_posts, True, pbar)
                    media_count += media_downloaded

                    media_downloaded = download_posts(extra_img_posts, False, pbar)
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
