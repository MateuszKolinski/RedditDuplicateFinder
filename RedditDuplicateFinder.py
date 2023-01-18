# Reddit Duplicate Finder
# Created by Mateusz Koliński (MateuszPKolinski@gmail.com)
# Fetches all submission titles on a specific subreddit via pushshift and then matches them with the current submission stream
# If names match, sends a report with previous submission IDs for moderators to check

import praw
import os
from configparser import ConfigParser
import traceback
import sys
import time
from pmaw import PushshiftAPI
import argparse
from datetime import datetime


# Reddit authentication #
def reddit_setup(config_path, error_sleep_minutes):
	# If config file exists
	if os.path.exists(config_path):
		connected = False
		while connected == False:
			try:
				# Read config file
				config_parser = ConfigParser()
				config_parser.read(config_path, encoding='utf-8')

				# Try connecting to reddit
				reddit = praw.Reddit(
				client_id=config_parser.get('setup', 'client_id'),
				client_secret=config_parser.get('setup', 'client_secret'),
				password=config_parser.get('setup', 'password'),
				user_agent=config_parser.get('setup', 'user_agent'),
				username=config_parser.get('setup', 'username')
				)

				add_log("Successfuly logged in to reddit.")
				connected = True
			except Exception as e:
				add_log(traceback.format_exc())
				add_log(f"Authentication to reddit failed. Config_path: {config_path}. Retrying in {error_sleep_minutes} minutes.")
				time.sleep(60*error_sleep_minutes)
	else:
		print("No config file detected. Exiting.")
		sys.exit()

	# Doesn't do anything at the moment, but apparently will be required at some point #
	reddit.validate_on_submit = True

	return reddit


# Log in to pushshift to retrieve deleted comments and submissions
def pushshift_setup(error_sleep_minutes):
	# Infinite loop which is broken (return statement) when we successfully log into pushshift
	while True:
		try:
			pushshift_api = PushshiftAPI()
			add_log("Successfuly logged into pushshift")
			return pushshift_api
		except Exception as e:
			add_log(traceback.format_exc())
			add_log(f"Cannot connect to PushshiftAPI. Retrying in {error_sleep_minutes} minutes.")
			time.sleep(60*error_sleep_minutes)


def find_duplicates(config_path, error_sleep_minutes, subreddit_name, report_message):
	# Log in to pushshift
	pushshift = pushshift_setup(error_sleep_minutes)

	# Get all submissions on a subreddit
	incomplete = True
	while incomplete:
		try:
			all_submissions = list(pushshift.search_submissions(subreddit=subreddit_name))
			incomplete = False
		except Exception as e:
			add_log(traceback.format_exc())
			add_log(f"Encountered an error while fetching all submissions on a subreddit. Retrying in {error_sleep_minutes} minutes. Relogging into pushshift.")
			time.sleep(60 * error_sleep_minutes)

			pushshift = pushshift_setup(error_sleep_minutes)

	# Log in to reddit
	reddit = reddit_setup(config_path, error_sleep_minutes)

	# Get current time
	previous_backup_time = time.time()

	# Cotninous loop
	while True:
		try:
			# Submission stream catching new submissions
			for submission in reddit.subreddit(subreddit_name).stream.submissions(skip_existing=True):
				add_log(f"Checking submission: {submission.title} by {submission.author.name}.")
				duplicates_list = []

				# Loop over all submissions
				for historical_submission in all_submissions:
					# If currently looped submission title is the same as submission's title in a stream, append its ID to the duplicate list
					if submission.title == historical_submission["title"] and submission.id != historical_submission["id"]:
						duplicates_list.append(historical_submission["id"])
		
				# If there are any duplicates
				if len(duplicates_list) > 0:
					# Create report message
					for i, duplicate in enumerate(duplicates_list):
						if i == 0:
							message = report_message + duplicate
						else:
							# Maximum number of characters is 100 according to PRAW
							# Users can send bigger report messages via site though
							if len(message + ", " + duplicate) < 100:
								message = message + ", " + duplicate
			
					# Report that submission
					submission.report(message)
					add_log(f"Reported {submission.title} by {submission.author.name} with message {message}")
		
				# Update the list of all submissions
				new_submissions = list(pushshift.search_submissions(subreddit=subreddit_name, after=int(previous_backup_time)))
				for new_submission in new_submissions:
					all_submissions.append(new_submission)

				previous_backup_time = time.time()

		except Exception as e:
			add_log(traceback.format_exc())
			add_log(f"Encountered an exception while finding duplicates. Retrying in {error_sleep_minutes} minutes. Relogging into reddit and pushshift.")
			time.sleep(60 * error_sleep_minutes)

			reddit = reddit_setup(config_path, error_sleep_minutes)
			pushshift = pushshift_setup(error_sleep_minutes)


# Print logs with their corresponding time and also add them to the log file
def add_log(text):
	try:
		datetime_now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		full_log = "[" + str(datetime_now) + "]: " + str(text)

		print(full_log)
		with open(log_path, "a", encoding="utf-8") as file:
			file.write(full_log + "\n")
	except Exception as e:
		print(traceback.format_exc())
		print(f"Something went wrong while adding a log: {text}.")


def main():
	# Parse optional arguments
	parser = argparse.ArgumentParser(description="Reddit Duplicate Finder")
	parser.add_argument("--subreddit_name", default="Polska", help="Target subreddit name", type=str)
	parser.add_argument("--config_path", default="config.ini", help="Config path and file name", type=str)
	parser.add_argument("--error_sleep_minutes", default=5, help="Time in minutes after an error", type=int)
	parser.add_argument("--log_path", default="RedditDuplicateFinder_logs.txt", help="File path and name of a txt log file", type=str)
	parser.add_argument("--report_message", default="Possible duplicate. ", help="Message sent in open report form", type=str)
	args = parser.parse_args()

	# Log path and file name
	# It's global because it's used everywhere
	global log_path
	log_path = args.log_path

	# Function for finding duplicates
	find_duplicates(args.config_path, args.error_sleep_minutes, args.subreddit_name, args.report_message)


if __name__ == "__main__":
	main()
