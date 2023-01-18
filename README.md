# Reddit Duplicate Finder
Created by Mateusz Koliński (MateuszPKolinski@gmail.com)

A Python script for finding and reporting duplicate Reddit submissions as a moderator.

Fetches all submission titles on a specific subreddit via pushshift and then matches them with the current submission stream.

If names match, script sends a report with previous submission's IDs for moderators to check and act upon.

Requires a .ini file configured as follows:

[setup]
client_id = 
client_secret = 
password = 
user_agent = 
username = 
