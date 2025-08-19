
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import telegram
import sys
import json # Added this line

# --- Constants ---
GOOGLE_SHEET_NAME = 'english vocab'  # Name of your Google Sheet
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_IDS = os.environ.get('TELEGRAM_CHAT_IDS', '').split(',')
SENT_WORDS_TRACKER_FILE = 'sent_words_tracker.txt'
GOOGLE_CREDENTIALS_JSON = os.environ.get('GOOGLE_CREDENTIALS_JSON')

# --- Google Sheets Connection ---
def get_google_sheet():
    """Connects to the Google Sheet and returns the worksheet."""
    try:
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        
        if not GOOGLE_CREDENTIALS_JSON:
            raise ValueError("GOOGLE_CREDENTIALS_JSON environment variable not set.")
            
        creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON) # Changed eval() to json.loads()
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        return sheet
    except Exception as e:
        print(f"Error connecting to Google Sheets: {e}")
        sys.exit(1)

# --- Telegram Bot ---
def send_telegram_message(bot, chat_id, message):
    """Sends a message to a Telegram chat."""
    try:
        bot.send_message(chat_id=chat_id, text=message, parse_mode=telegram.ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")

# --- Core Logic ---
def send_daily_words():
    """Fetches and sends 3 new words to the Telegram chats."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_IDS:
        print("Telegram token or chat IDs are not set.")
        return

    bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
    sheet = get_google_sheet()
    words = sheet.get_all_records()

    try:
        with open(SENT_WORDS_TRACKER_FILE, 'r') as f:
            last_sent_index = int(f.read().strip())
    except FileNotFoundError:
        last_sent_index = 0

    new_words = words[last_sent_index : last_sent_index + 3]

    if not new_words:
        message = "No new words to send today!"
    else:
        message_parts = []
        for word in new_words:
            word_entry = (
                f"*Word:* {word['Word']}\n"
                f"*Meaning:* {word['Meaning']}\n"
                f"*Synonyms:* {word['Synonyms']}\n"
                f"*Antonyms:* {word['Antonyms']}\n"
                f"*Example:* {word['Example Sentence']}"
            )
            message_parts.append(word_entry)
        message = "\n\n---\n\n".join(message_parts)

    for chat_id in TELEGRAM_CHAT_IDS:
        if chat_id:
            send_telegram_message(bot, chat_id, message)

    # Update the tracker
    with open(SENT_WORDS_TRACKER_FILE, 'w') as f:
        f.write(str(last_sent_index + len(new_words)))

if __name__ == "__main__":
    # This allows us to run different functions based on arguments
    # We will use this in our GitHub Actions workflow
    if len(sys.argv) > 1:
        if sys.argv[1] == 'daily_words':
            send_daily_words()
        # Add other functions like 'weekly_summary' and 'quiz' here later
    else:
        print("No task specified.")
