# Change Log

## Version 0.7

- Changed "dynamicRules" link which solves the "'str' object does not support item assignment" issue.
- Improved subscriber cache -- now detects when you subscribe to a new profile and automatically updates without manually deleting the .json file.
- Added new profile cache (when you visit a profile for the first time and need to re-enter the profile to download only the latest media, now with the cache you don't have to make all the requests from scratch.. (excluding stories / chat / highlights)
- Added "#!/usr/bin/env python3"
- Made the #ADV blocks more robust by adding new tag blocks + DM.
- Further UI improvements will be made in the future.
- And other small things.. more ideas will be added in the future.

## Version 0.6

+ Changed the application name from "OF-SCR" to "OnlySnap".
+ Added the ability to download messages, streams, stories, and highlights.
+ Implemented cache handling for user IDs and SUB.
+ Introduced a function to create signed headers for the API requests.
+ Incorporated a function to fetch all highlights.
+ Extended the API request function to support multiple endpoint types.
+ Optimized the process of fetching all video, photo, archived, and stream posts.
+ Included functions to download chat media.
+ Added a function to live print messages for better UI experience.
+ Improved error handling and added checks for media availability.
+ General code improvements and bug fixes.
+ Added "https://github.com/jordon31/OnlySnap/issues/13" function (Download Post with txt need only "disable_download_post_with_txt": True, on " `False`")
+ Added "https://github.com/jordon31/OnlySnap/issues/12" and "https://github.com/jordon31/OnlySnap/pull/14"

## Version 0.5

+ New video tutorial: https://youtu.be/JNKRDsodCTc
+ Added a feature to automatically skip files that contain "@" tags.
+ Photos and Videos folders are now placed inside a "Media" folder for cleaner organization.
+ Avatar and header photos are placed in a folder called "Public".
+ Fixed the issues mentioned here "https://github.com/jordon31/OF-SCR/issues/6".
+ Tested on Mac and everything works fine.
+ Improved the UI console.
+ Fixed other minor bugs.

## Version 0.4

+ Added a feature to automatically creation of the 'TaggedPosts' folder based on years and weeks.
* Improved overall performance and stability.
* Enhanced user interface.
* Removed the 'C' button only when scraping all subs.. for individual users it remains.
* Other improvements.
* Fixed bugs and errors.

## Version 0.3

+ Added a function to skip files that contain "@" tags.
+ Added advanced search feature.
* Improved loading bar.
* Fixed file count when continuing downloads.
* Other improvements.

When you continue a download, the message "DOWNLOADED " + str(new_files) + " NEW FILES" is not reset.

## Version 0.2

+ Improved folder organization.
+ Added folders:
    - Today
    - Yesterday
    - Last Week

## Version 0.1

+ Added a start menu.
+ Added more Emoij to delete + \n in .json file (More Clean).
+ Added title to console.
* Fixed a folder problem that caused folders to be created even if the content was not on the OF profile.
* Other fixes.
