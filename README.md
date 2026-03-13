**Yoooo**

This project was **COOKED**. Deadass forgotten for 3 years. But I locked in, cracked a Monster, and rewrote the whole thing.

We ain't using basic scripts anymore. We got a **TUI** (Terminal User Interface).

**Check this out:** No more sweating over `cmd` commands or typing manual inputs.
You can letterally **CLICK** on stuff now.

It's stupid easy. Other tools out there require a PhD in coding to run; mine is built different. **EZ.** No complex garbage, just click and download.

## HOW TO START (video for fast)

`.bat` for fast

1.  **Python 3.10+** required.
2.  Install requirements: `pip install -r requirements.txt` (Now includes **Pillow** for the Watermark magic).
3.  Click `!run.bat`.
4.  Video: [tutorial](https://youtu.be/5tMwjg5hXNY)

### THE LAUNCHER

Inside `!run.bat` you have 2 options. Don't mess this up.

* **[1] START ONLYSNAP:**
    * Opens the main app.
* **[2] AUTO-PASTE (DO THIS FIRST!):**
    * Go to Browser -> F12 -> Network -> Click on "Fetch/XHR" -> chat api for no miss nothing. [chats](https://onlyfans.com/my/chats)
    * Copy the headers/request.
  
    *  ![Screenshot Cookies](https://i.postimg.cc/TwS30f62/Screenshot-2026-02-09-021826.png)
    
    * Run Option 2. The script **yeets** the cookies straight into the config. No manual copy-paste struggle.

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

## 📸 SMART WATERMARK

We added a high-end **Auto-Marker** for photos.

* **Dynamic Sizing:** It detects the photo resolution and adapts the text size so it's never too big or too small.
* **Elegant Design:** White text, subtle shadow, and a semi-transparent dark background in the bottom-left corner.
* **How to use:** Just put your text in Settings. If you want a specific vibe, drop your favorite `.ttf` font into the main folder.

---

## 🔧 EXTRAS

* **Telegram:** [https://t.me/OnlySnap0](https://t.me/OnlySnap0)
* **Credits:** Me. I built this while you were sleeping.
* **Bugs:** It works on my machine. (any problem / suggestion open issues)
* **Disclaimer:** For educational purposes only (wink wink).

OnlyFans Scrape - Scrape OnlyFans
