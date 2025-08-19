
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import telegram
import sys
import json
import asyncio # Added this line

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
async def send_telegram_message(bot, chat_id, message):
    """Sends a message to a Telegram chat."""
    try:
        await bot.send_message(chat_id=chat_id, text=message, parse_mode=telegram.constants.ParseMode.MARKDOWN)
    except Exception as e:
        print(f"Error sending message to {chat_id}: {e}")

# --- Core Logic ---
async def send_daily_words():
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
        for i, word in enumerate(new_words):
            word_entry = (
                f"*Word:* {word['Word']}\n"
                f"*Meaning:* {word['Meaning']}\n"
                f"*Synonyms:* {word['Synonyms']}\n"
                f"*Antonyms:* {word['Antonyms']}\n"
                f"*Example:* {word['Example Sentence']}"
            )
            message_parts.append(f"*{i+1}.* {word_entry}")
        message = "\n\n---\n\n".join(message_parts)

    for chat_id in TELEGRAM_CHAT_IDS:
        if chat_id:
            await send_telegram_message(bot, chat_id, message)

    # Update the tracker
    with open(SENT_WORDS_TRACKER_FILE, 'w') as f:
        f.write(str(last_sent_index + len(new_words)))

async def send_weekly_summary():
    """Fetches and sends a summary of the last 21 words learned."""
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

    # Calculate the range for the last 21 words (3 words/day * 7 days)
    start_index = max(0, last_sent_index - 21)
    summary_words = words[start_index:last_sent_index]

    if not summary_words:
        message = "No words learned this week yet for a summary."
    else:
        message_parts = ["*Weekly Vocabulary Summary:*"]
        for i, word in enumerate(summary_words):
            word_entry = (
                f"*Word:* {word['Word']}\n"
                f"*Meaning:* {word['Meaning']}\n"
                f"*Synonyms:* {word['Synonyms']}\n"
                f"*Antonyms:* {word['Antonyms']}\n"
                f"*Example:* {word['Example Sentence']}"
            )
            message_parts.append(f"\n---\n\n*{i+1}.* {word_entry}")
        message = "\n".join(message_parts)

    for chat_id in TELEGRAM_CHAT_IDS:
        if chat_id:
            await send_telegram_message(bot, chat_id, message)

if __name__ == "__main__":
    # This allows us to run different functions based on arguments
    # We will use this in our GitHub Actions workflow
    if len(sys.argv) > 1:
        if sys.argv[1] == 'daily_words':
            asyncio.run(send_daily_words())
        elif sys.argv[1] == 'weekly_summary':
            asyncio.run(send_weekly_summary())
        # Add other functions like 'quiz' here later
    else:
        print("No task specified.")
