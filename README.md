# OF Scraper

OF Scraper is a Python script that lets you download content from OnlyFans profiles that you're subscribed to.

## Features

- Download photos, videos, and archived posts from any OnlyFans profile you're subscribed to.
- Download avatar and header images for each profile.
- Save profile information, including name, username, and bio, in a JSON file.
- Automatically detects and skips already downloaded files.
- Downloads files in parallel to enhance download speed.
- Folder organization has been improved for better content management.
- Advanced search feature to find content based on keywords.
- Automatically skip files containing "@" tags and posts with "#adv".

## Requirements

- Python 3.x.x
- Requests library

## Installation

1. Clone the repository or download the source code.
2. Install the required Python libraries by running `pip install -r requirements.txt`.
3. If the Requests library is not already installed on your machine, you can install it by running `pip install requests`.
4. Edit the `auth.json` file with your user agent, user ID, x-bc, and session token.
5. Watch the tutorial video at "https://youtu.be/JNKRDsodCTc" for more detailed instructions.

## Usage

To start the script, run the python file `of-scr.py`. The script will ask you to select the profile you want to download content from, using the auto-complete feature for profile names (TAB). You can use the TAB key at the start of the search to see the complete list of profiles and select with the arrow keys.

The downloaded content will be saved in a directory named "profiles" in the same location as the script. Each profile will have its own subdirectory, containing folders for photos, videos, avatar, header, and archived posts.

### Advanced Search

To search for content based on keywords, enter a query when prompted to select a profile. The script will return all posts that contain the specified keyword(s).

## Known Issues

- The script may not work if the OnlyFans API changes.
- Due to the nature of the content, the script may not work with some profiles.

## Disclaimer

This script is for educational purposes only. Please respect the content creators' rights and only use the downloaded content for personal use. Do not share or distribute the content without the creator's consent.

## GPL-3

OF Scraper is distributed under the terms of the GNU General Public License version 3 (GPLv3). This license grants you the freedom to use, modify, and distribute the software under certain conditions.

OF Scraper is based on the source code of "[onlyfans-dl](https://github.com/k0rnh0li0/onlyfans-dl)". Some changes have been made to the code and the project has been uploaded to my GitHub account.

We welcome anyone interested to contribute to the project's growth. If you modify the code and distribute it, you must also make your changes available under the GPLv3 license.

To learn more about the GPLv3 license, please visit https://www.gnu.org/licenses/gpl-3.0.en.html.
