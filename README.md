# OF Scraper

OF Scraper is a Python script that allows you to download content from OnlyFans profiles you are subscribed to.

## Features

- Download photos, videos, and archived posts from any OnlyFans profile you're subscribed to.
- Download avatar and header images for each profile.
- Save profile information, including name, username, and bio, in a JSON file.
- Automatically detects and skips already downloaded files.
- Downloads files in parallel to improve download speed.
- Carefully worked on the organization of the folders according to the years of the posts

## Requirements

- Python 3.x.x
- Requests library

## Installation

1. Clone the repository or download the source code.
2. Install the required Python libraries by running `pip install -r requirements.txt`.
3. Edit the `auth.json` file with your user agent, user ID, x-bc, and session token.
4. VIDEO: "https://youtu.be/F2AP5czkdbA"

## Usage

To start the script, run `python of-scr.py`. The script will prompt you to enter the number corresponding to the profile you want to download content from. You can also download content from multiple profiles at once by entering multiple numbers separated by commas. To download content from all profiles, enter "0".

The downloaded content will be saved in a directory named "profiles" in the same location as the script. Each profile will have its own subdirectory, containing folders for photos, videos, avatar, header, and archived posts.

## Known Issues

- The script may not work if the OnlyFans API changes.
- Due to the nature of the content, the script may not work with some profiles.

## Disclaimer

This script is for educational purposes only. Please respect the content creators' rights and only use the downloaded content for personal use. Do not share or distribute the content without the creator's consent.

## GPL-3

OF Scraper is distributed under the terms of the GNU General Public License version 3 (GPLv3). The project comes from the source code of "[onlyfans-dl](https://github.com/k0rnh0li0/onlyfans-dl)". I made some code changes and posted the project to my GitHub account.

These changes. I hope this project will be useful for other users and we invite anyone interested to contribute to its growth.
