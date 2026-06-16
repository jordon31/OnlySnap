**Yoooo 3 years** 

**OnlySnap** — the easiest OnlyFans & Patreon downloader out there. No cap.

Full **TUI** (Terminal User Interface). No more sweating over `cmd` commands or typing manual inputs.
You can literally **CLICK** on stuff now.

Other tools require a PhD in coding to run; this one is built different. **EZ.** No complex garbage, just click and download.

---

## 🚀 HOW TO START

### Requirements

- **Python 3.10+** required
- **pip** (comes with Python)

### Windows

1. Double-click **`!RUN.bat`**

### Linux / macOS

```bash
chmod +x run.sh
./run.sh
```
Same menu, same options. Works on Ubuntu, Fedora, Arch, macOS (Intel + Apple Silicon).

📺 Video tutorial: [YouTube](https://youtu.be/dQw4w9WgXcQ)

---

## 🎛️ THE LAUNCHER

### Windows (`!RUN.bat`)

| Option | What it does |
| --- | --- |
| **1) Run OnlySnap** | Opens the main TUI hub |
| **2) Install Requirements** | `pip install -r Site\requirements.txt` — installs all dependencies |
| **3) Install DRM Tools** | Downloads FFmpeg, MP4Decrypt, N_m3u8DL-RE into `dmr/` folder |
| **4) Add to PATH** | Creates `onlyfans`, `patreon`, `onlysnap` commands usable from any folder |

### Linux / macOS (`run.sh`)

Same 4 options. DRM tools are installed via:
- **macOS**: Homebrew (auto-installs Brew if missing) + GitHub releases
- **Linux**: `apt`/`dnf`/`pacman`/`apk` for FFmpeg + binary downloads for the rest

---

## 🔑 AUTO COOKIE SCRAPE (DO THIS FIRST!)

No more manual copy-paste of cookies. The app **auto-scrapes your browser session** directly.

### How it works

1. Open OnlySnap → Select **OnlyFans** or **Patreon**
2. The cookie scraper launches **your actual browser** (with your logged-in profile)
3. It opens the site, grabs cookies automatically, and saves them to `Auth.json`
4. **Done.** No DevTools, no manual JSON editing.

### Supported Browsers (auto-detected)

| Browser | Windows | macOS | Linux |
| --- | --- | --- | --- |
| **Chrome** | ✅ | ✅ | ✅ |
| **Brave** | ✅ | ✅ | ✅ |
| **Edge** | ✅ | ✅ | ✅ |
| **Opera** | ✅ | ✅ | — |
| **Opera GX** | ✅ | — | — |
| **Firefox** | ✅ | ✅ | ✅ |
| **Vivaldi** | ✅ | ✅ | ✅ |
| **Safari** | — | ❌ (not supported by Playwright) | — |

> ⚠️ **Important:** The browser must be **fully closed** before running the cookie scrape. The scraper opens your real profile — it can't share the lock with an already-open browser.

### Headless / Server Mode (Linux without GUI)

If you're on a Linux server with no desktop, the auto-scrape detects it automatically:
- It skips the browser launch and prompts you to **paste your cookies manually** in the terminal
- The script then saves them to `Auth.json` for you — no need to edit JSON files by hand

---

## 🛤️ PATH COMMANDS (Option 4)

Run **Option 4** in the launcher to register global commands:

```
onlyfans    → Launches OnlyFans scraper from anywhere
patreon     → Launches Patreon scraper from anywhere
onlysnap    → Launches the main hub from anywhere
```

### How it works

- **Windows:** Creates wrapper `.bat` files in `%USERPROFILE%\.onlysnap\bin\` and adds it to your `PATH`
- **Linux/macOS:** Creates wrapper scripts in `~/.onlysnap/bin/` and adds it to your `~/.bashrc` / `~/.zshrc` / `fish config`

### If you move the folder

Just re-run **Option 4**. It rewrites the wrapper scripts with the new paths. Works across drives too.

> 💡 Open a **new terminal** after running Option 4 for the first time — the PATH update won't apply to the current session.
 ----------
 --- Example
 <a href="https://postimg.cc/SX6PR85Y" target="_blank">
  <img src="https://i.postimg.cc/yNtCfyyj/example.gif" alt="Registrazione">
</a>

---

## ⚙️ SETTINGS (STOP EDITING JSON FILES)

You don't need to touch `Config.json` like a caveman anymore. 

Inside the app, there is a **[SETTINGS]** button. Click it.
**BIG NEWS:** Everything you change is **AUTO-SAVED IN REAL-TIME**. No "Save" button, no "I forgot to click apply". You type, it saves. Period.

| Setting | Translation for Dummies |
| --- | --- |
| **Custom Filename** | Add your branding (es. `@MyChannel`). Leave empty for original IDs. |
| **Watermark Text** | Type your text. It adds a sleek, dynamic watermark on every photo. |
| **Month Names** | `true` = "January", `false` = Numbers. Aesthetic choice. |
| **No Year Folders** | If `true`, it dumps everything in one place. Chaotic evil. |
| **Skip Highlights Covers** | Saves space. Who looks at covers anyway? |
| **Disable Text Files** | `true` = Only Media. `false` = Includes a `.txt` with the post caption. |
| **Download Tagged** | Downloads SPAM/ADS (#ad). Keep it `false` unless you love commercials. |
| **Workers (Threads)** | Speed. Default is 5. High values = Fast, but don't fry your CPU. |

---

## ⚠️ ATTENTION: FILENAME LOGIC

Read this or don't complain later.
The script checks if a file exists by its **Name**.

* If you set a **Custom Filename Prefix** (e.g., `MyStore_12345.jpg`), the script saves it like that.
* If you later **DELETE** the prefix or change it, the script will look for `12345.jpg`, won't find it, and **WILL DOWNLOAD EVERYTHING AGAIN**.

---

## ❤️ PATREON: SPAM LIKE (Bonus Feature)

Auto-like all posts from a creator on Patreon.

### Setup

The SPAM LIKE button only appears if you have a valid **CSRF token** in your Auth.json:

1. Open Patreon in your browser → **F12** → **Network** tab
2. Click the ❤️ like button on any post
3. Find the **POST** request to `/api/posts/.../likes`
4. In **Request Headers**, copy the value of `x-csrf-signature`
5. Paste it in `Site/Configs/Patreon/Auth.json`:

```json
{
    "user-agent": "...",
    "cookie": "...",
    "x-csrf-signature": "paste_your_token_here"
}
```

6. Restart Patreon → The **SPAM LIKE** button appears

### How it works

- Fetches all posts from the selected creator
- Skips locked posts (higher tier) and already-liked posts
- Likes at ~150 posts/min with built-in delay between requests
- If Patreon rate-limits you (429), the script stops immediately

---

## 📸 SMART WATERMARK

We added a high-end **Auto-Marker** for photos.

* **Dynamic Sizing:** It detects the photo resolution and adapts the text size so it's never too big or too small.
* **Elegant Design:** White text, subtle shadow, and a semi-transparent dark background in the bottom-left corner.
* **How to use:** Just put your text in Settings. If you want a specific vibe, drop your favorite `.ttf` font into the main folder.

---

## 🔄 AUTO UPDATE CHECK

Both **OnlyFans.py** and **Patreon.py** automatically check for updates on startup by comparing your local version with the latest on GitHub. If a new version is available, you'll see a notification in the TUI.

---

## 📁 PROJECT STRUCTURE

```
OnlySnap-main/
├── OnlySnap.py          # Main TUI hub
├── !RUN.bat             # Windows launcher
├── run.sh               # Linux/macOS launcher
├── Site/
│   ├── OnlyFans.py      # OnlyFans downloader TUI
│   ├── Patreon.py        # Patreon downloader TUI
│   ├── cookie-onlyfans.py  # Auto cookie scraper (OnlyFans)
│   ├── cookie-patreon.py   # Auto cookie scraper (Patreon)
│   ├── requirements.txt    # Python dependencies
│   ├── Configs/
│   │   ├── OnlyFans/
│   │   │   ├── Auth.json    # Cookies & headers
│   │   │   └── Config.json  # Download settings
│   │   └── Patreon/
│   │       ├── Auth.json    # Cookies, headers & CSRF token
│   │       └── Config.json  # Download settings
│   └── dmr/               # DRM tools (FFmpeg, mp4decrypt, N_m3u8DL-RE)
└── downloads/             # Your downloaded content
```

---

## 🔧 EXTRAS

* **Telegram:** [https://t.me/OnlySnap0](https://t.me/OnlySnap0)
* **Credits:** Me. I built this while you were sleeping.
* **Bugs:** It works on my machine. (any problem / suggestion open issues)
* **Disclaimer:** For educational purposes only (wink wink).

OnlyFans Scrape - Scrape OnlyFans - Patreon Scrape - Scrape Patreon
