# Changelog

All notable changes to this project will be documented in this file.

## [1.0.6] - 2026-06-16

### Added
- **Patreon Full Integration:** Complete Patreon downloader TUI (`Patreon.py`) with creator list, collection/feed sync, caching, and parallel downloads.
- **Auto Cookie Scrape:** Both OnlyFans and Patreon now have auto cookie scrapers (`cookie-onlyfans.py`, `cookie-patreon.py`) that open your actual browser profile, grab cookies, and save them to `Auth.json` automatically. No more manual copy-paste from DevTools.
- **Multi-Browser Support:** Auto-detects and supports Chrome, Brave, Edge, Opera, Opera GX, Firefox, and Vivaldi on Windows, macOS, and Linux. Opens your real browser profile (not a new one).
- **Linux / macOS Launcher:** New `run.sh` script with the same 4 options as `!RUN.bat`. DRM tools install via package managers (Homebrew on macOS, apt/dnf/pacman/apk on Linux) and GitHub releases.
- **PATH Commands (Option 4):** Register `onlyfans`, `patreon`, and `onlysnap` as global terminal commands. Works from any folder, any drive. Re-run Option 4 after moving the project folder to update paths.
- **Patreon SPAM LIKE:** Auto-like all viewable posts from a creator. Skips locked posts and already-liked posts. Button only appears when `x-csrf-signature` is set in Auth.json. Stops immediately on rate limit (429).
- **Auto Update Check:** Both `OnlyFans.py` and `Patreon.py` check for updates on startup by comparing local version with GitHub.
- **Centralized Versioning:** `OnlyFans.py` and `Patreon.py` dynamically read `CURRENT_VERSION` and `GITHUB_RAW_URL` from the main `OnlySnap.py` — change it in one place.
- **Dependency Management:** New `Site/requirements.txt` file. `!RUN.bat` Option 2 replaced "Auto Paste" with "Install Requirements" (`pip install -r`).
- **DRM Tools Installer:** Option 3 downloads FFmpeg, mp4decrypt (Bento4), and N_m3u8DL-RE with correct URLs per platform and architecture (x64/arm64).
- **Headless / Server Mode:** Cookie scripts auto-detect headless Linux (no GUI) and prompt for manual cookie input in the terminal.
- **Browser Close Detection:** Added `is_browser_running()` check using `tasklist` (Windows) / `pgrep` (Linux/macOS) before launching cookie scrape to prevent profile lock conflicts.

### Changed
- **`!RUN.bat` Overhauled:** Now has 4 options (Run, Install Requirements, DRM Tools, Add to PATH) instead of the old 2-option layout.
- **README.md Rewritten:** Full documentation covering all features, browser support table, project structure, and setup for all platforms.

--------------------------------------------
## [1.0.5] - 2026-03-27

### Fixed
- **DRM Handling:** Prevented the script from saving corrupted/unplayable .mp4 files when the key server is offline. The script now safely skips these files. Because no broken file is saved, the script will naturally try to download them again the next time you sync that specific creator.
- **Dump Json:** Improved
- **New Site:**  Patreon integration so the file structure will change (next update)

--------------------------------------------
## [1.0.4] - 2026-03-13

### Fixed 
- **API Adaptation:** Updated the downloader to handle the recent OnlyFans API change. Photo post responses shifted from arrays to objects ({"list": [...]}); the script now correctly parses the new format to prevent skipped downloads.

⚠️⚠️ ***NEED DELETE OLD CACHE***⚠️⚠️

### Added 
- **Dynamic Text Watermark:** New feature to automatically apply a customizable watermark to photos. It auto-detects resolution to ensure perfect scaling and includes a subtle semi-transparent background for readability.
- **Custom Filename Prefix:** Added the ability to set a personalized prefix (e.g., @YourTag or any) for all downloaded files directly from the settings.
- **New Dependency:** Added `Pillow` (PIL) 
--------------------------------------------
## [1.0.3] - 2026-03-09

### Fixed
- **Chats DRM:** Fixed and now full supported

--------------------------------------------
## [1.0.2] - 2026-02-25

### Added
- **Chat DRM Support:** Added suppart for downloading DRM-protected media from direct messages. *(Note: This feature is currently untested as I haven't encountered DRM-protected chat content to fully verify it yet).*
- **External API Update:** Updated the external backend API to properly handle and route license requests for encrypted chat messages using the `/drm/message/` endpoint.

### Fixed
- **Completion Message Crash:** Fixed a `NameError` crash caused by a typo (`total_global_failes` -> `total_global_files`) that occurred when no new files needed downloading.
- **Debug Logging:** Fixed an issue where debug logging would silently fail.
- **DRM Race Condition:** Fixed a critical race condition during parallel DRM downloads.
