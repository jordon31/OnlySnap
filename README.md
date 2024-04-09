# OnlySnap

OnlySnap is a versatile Python script that allows you to seamlessly download content from your subscribed OnlyFans profiles. Whether you're using Windows, Mac, or Linux, OnlySnap ensures you have easy access to your favorite content.

## Features

- Download photos, videos, archived posts, streams, stories, highlights, and chat messages from any OnlyFans profile you're subscribed to.
- Download avatar and header images for each profile.
- Save profile information, including name, username, and bio, in a JSON file.
- Automatically detects and skips already downloaded files.
- Enhanced download speed with parallel downloads.
- Improved folder organization for efficient content management.
- Advanced search feature lets you find content based on keywords.
- Customize your experience with the configuration file. Adjust settings like folder organization, media download preferences, and more.
- Supports downloading content from tagged posts and organizes them into a separate folder.

## Requirements

- Python 3.x.x
- Requests library

## Installation

1. Clone the repository or download the source code.
2. Install the required Python libraries by running `pip install -r requirements.txt`.
4. Rename `Auth.json.example` to `Auth.json` and `Config.json.example` to `Config.json`
5. Edit the `Auth.json` file with your user agent, user ID, x-bc, and session token.
6. For Tutorial install watch the tutorial "https://youtu.be/JNKRDsodCTc"

## Configuration

OnlySnap comes with a configuration file Config.json that allows you to customize various aspects of the script. Here's a brief overview:

- Folder Organization: Choose whether to use month names, month numbers, or organize without year folders.
- Highlights: Decide if you want to download cover highlights or organize them in individual folders.
- Post Management: Toggle the creation of a unified 'Posts' folder, or download posts with specific tags.
- Concurrent Downloads: Specify the number of threads for simultaneous downloads.
- Check out `Config.json.example` for more details on each setting.

## Usage

To start the script, run the python file `OnlySnap.py`. The script will prompt you to select a profile from which you want to download content. Use the TAB key for auto-complete or to see the complete list of profiles.

The downloaded content is saved in a directory named "profiles" in the same location as the script. Each profile gets its own subdirectory, which contains folders for photos, videos, avatar, header, archived posts, and more.

### Advanced Search

To search for content based on keywords, simply enter a query when prompted to select a profile. The script will return all posts containing the specified keyword(s).

## Known Issues

- The script may not work if the OnlyFans API changes.
- Due to the nature of the content, the script may not work with some profiles.

## Disclaimer

This script is for educational purposes only. Please respect the content creators' rights and only use the downloaded content for personal use. Do not share or distribute the content without the creator's consent.

## GPL-3

OnlySnap is distributed under the terms of the GNU General Public License version 3 (GPLv3). This license grants you the freedom to use, modify, and distribute the software under certain conditions.

OnlySnap is based on the source code of "[onlyfans-dl](https://github.com/k0rnh0li0/onlyfans-dl)". Some changes have been made to the code and the project has been uploaded to my GitHub account.

We welcome anyone interested to contribute to the project's growth. If you modify the code and distribute it, you must also make your changes available under the GPLv3 license.

To learn more about the GPLv3 license, please visit [https://www.gnu.org/licenses/gpl-3.0.en.html](https://www.gnu.org/licenses/licenses.html).
